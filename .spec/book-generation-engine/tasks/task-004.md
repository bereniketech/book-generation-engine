---
task: 004
feature: book-generation-engine
status: complete
model: haiku
supervisor: software-cto
agent: ai-ml-expert
depends_on: [002]
---

# Task 004: NotebookLM Client

## Skills
- .kit/skills/ai-platform/notebooklm/SKILL.md
- .kit/skills/languages/python-patterns/SKILL.md

## Agents
- @ai-ml-expert

## Commands
- /task-handoff

> Load the skills, agents, and commands listed above before reading anything else. Do not load context not listed here.

---

## Objective

Implement `worker/clients/notebooklm_client.py` that creates a NotebookLM notebook, adds the book topic as a source, triggers generation, fetches the research summary, and returns `None` on any API failure (caller synthesises via LLM fallback).

---

## Files

### Create
| File | Purpose |
|------|---------|
| `worker/clients/notebooklm_client.py` | NotebookLM API wrapper with graceful fallback |
| `tests/unit/test_notebooklm_client.py` | Unit tests for happy path + fallback |

---

## Dependencies

```bash
# httpx already in pyproject.toml.
# New env var (add to .env.example if not present):
# GOOGLE_API_KEY is already there — NotebookLM uses the same key.
```

---

## API Contracts

```
Internal usage:
  client = NotebookLMClient(api_key="<google_api_key>")
  summary: str | None = client.research(topic="Stoicism and modern leadership", max_wait_seconds=120)
  # Returns None if API unavailable or times out
```

---

## Code Templates

### `worker/clients/notebooklm_client.py` (create this file exactly)
```python
"""NotebookLM API client for non-fiction deep research.

Graceful fallback: returns None on any network or API error.
The non-fiction pipeline synthesises a research summary via LLM when None is returned.
"""
from __future__ import annotations

import time
import logging

import httpx

logger = logging.getLogger(__name__)

NOTEBOOKLM_API_BASE = "https://notebooklm.googleapis.com/v1"


class NotebookLMClient:
    """Wraps the NotebookLM API. Returns None on failure — never raises."""

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self._headers = {"x-goog-api-key": api_key, "Content-Type": "application/json"}

    def research(self, topic: str, max_wait_seconds: int = 120) -> str | None:
        """Create a notebook, add the topic as a source, and return the generated summary.

        Returns None if the API is unavailable or generation times out.
        """
        try:
            notebook_id = self._create_notebook(topic)
            if notebook_id is None:
                return None
            source_added = self._add_text_source(notebook_id, topic)
            if not source_added:
                return None
            summary = self._wait_for_summary(notebook_id, max_wait_seconds)
            return summary
        except Exception as exc:
            logger.warning("NotebookLM research failed (will use LLM fallback): %s", exc)
            return None

    def _create_notebook(self, title: str) -> str | None:
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    f"{NOTEBOOKLM_API_BASE}/notebooks",
                    headers=self._headers,
                    json={"title": title[:100]},
                )
                response.raise_for_status()
                data = response.json()
                return data.get("name", "").split("/")[-1]
        except Exception as exc:
            logger.warning("NotebookLM create_notebook failed: %s", exc)
            return None

    def _add_text_source(self, notebook_id: str, text: str) -> bool:
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    f"{NOTEBOOKLM_API_BASE}/notebooks/{notebook_id}/sources",
                    headers=self._headers,
                    json={"text_content": {"text": text}},
                )
                response.raise_for_status()
                return True
        except Exception as exc:
            logger.warning("NotebookLM add_source failed: %s", exc)
            return False

    def _wait_for_summary(self, notebook_id: str, max_wait_seconds: int) -> str | None:
        deadline = time.time() + max_wait_seconds
        with httpx.Client(timeout=30.0) as client:
            while time.time() < deadline:
                try:
                    response = client.get(
                        f"{NOTEBOOKLM_API_BASE}/notebooks/{notebook_id}",
                        headers=self._headers,
                    )
                    response.raise_for_status()
                    data = response.json()
                    # NotebookLM returns generated summary in notebook metadata
                    summary = data.get("summary") or data.get("description")
                    if summary:
                        return str(summary)
                except Exception as exc:
                    logger.warning("NotebookLM poll failed: %s", exc)
                time.sleep(5)
        logger.warning("NotebookLM summary timed out after %ds", max_wait_seconds)
        return None
```

### `tests/unit/test_notebooklm_client.py` (create this file exactly)
```python
"""Unit tests for NotebookLMClient."""
from unittest.mock import MagicMock, patch

import pytest

from worker.clients.notebooklm_client import NotebookLMClient


def _make_mock_http(responses: list) -> MagicMock:
    """Build a context-manager mock for httpx.Client with sequential responses."""
    mock_client = MagicMock()
    mock_client.__enter__ = lambda s: mock_client
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.post = MagicMock(side_effect=responses[:2])
    mock_client.get = MagicMock(side_effect=responses[2:])
    return mock_client


def test_research_happy_path_returns_summary():
    create_resp = MagicMock()
    create_resp.raise_for_status.return_value = None
    create_resp.json.return_value = {"name": "notebooks/nb-abc"}

    source_resp = MagicMock()
    source_resp.raise_for_status.return_value = None
    source_resp.json.return_value = {"id": "src-1"}

    poll_resp = MagicMock()
    poll_resp.raise_for_status.return_value = None
    poll_resp.json.return_value = {"summary": "Deep research summary about Stoicism."}

    with patch("worker.clients.notebooklm_client.httpx.Client") as MockClient, \
         patch("worker.clients.notebooklm_client.time.sleep"):

        def make_ctx(*args, **kwargs):
            ctx = MagicMock()
            ctx.__enter__ = lambda s: ctx
            ctx.__exit__ = MagicMock(return_value=False)
            return ctx

        clients = [
            _make_mock_http([create_resp, source_resp, poll_resp]),
        ]
        call_count = 0

        def client_factory(*args, **kwargs):
            nonlocal call_count
            m = MagicMock()
            m.__enter__ = lambda s: m
            m.__exit__ = MagicMock(return_value=False)
            if call_count == 0:
                m.post = MagicMock(return_value=create_resp)
            elif call_count == 1:
                m.post = MagicMock(return_value=source_resp)
            else:
                m.get = MagicMock(return_value=poll_resp)
            call_count += 1
            return m

        MockClient.side_effect = client_factory
        client = NotebookLMClient(api_key="test-key")
        result = client.research("Stoicism and modern leadership", max_wait_seconds=10)

    assert result == "Deep research summary about Stoicism."


def test_research_returns_none_when_api_unavailable():
    """When the API raises a network error, research() returns None without raising."""
    import httpx as _httpx

    with patch("worker.clients.notebooklm_client.httpx.Client") as MockClient:
        mock_ctx = MagicMock()
        mock_ctx.__enter__ = lambda s: mock_ctx
        mock_ctx.__exit__ = MagicMock(return_value=False)
        mock_ctx.post = MagicMock(
            side_effect=_httpx.ConnectError("Connection refused")
        )
        MockClient.return_value = mock_ctx

        client = NotebookLMClient(api_key="test-key")
        result = client.research("Any topic", max_wait_seconds=10)

    assert result is None


def test_research_returns_none_on_timeout():
    """When polling times out, research() returns None."""
    create_resp = MagicMock()
    create_resp.raise_for_status.return_value = None
    create_resp.json.return_value = {"name": "notebooks/nb-xyz"}

    source_resp = MagicMock()
    source_resp.raise_for_status.return_value = None

    # Poll always returns no summary
    poll_resp = MagicMock()
    poll_resp.raise_for_status.return_value = None
    poll_resp.json.return_value = {"summary": None}

    with patch("worker.clients.notebooklm_client.httpx.Client") as MockClient, \
         patch("worker.clients.notebooklm_client.time.sleep"), \
         patch("worker.clients.notebooklm_client.time.time", side_effect=[0, 0, 999, 999]):

        call_count = 0

        def client_factory(*args, **kwargs):
            nonlocal call_count
            m = MagicMock()
            m.__enter__ = lambda s: m
            m.__exit__ = MagicMock(return_value=False)
            if call_count == 0:
                m.post = MagicMock(return_value=create_resp)
            elif call_count == 1:
                m.post = MagicMock(return_value=source_resp)
            else:
                m.get = MagicMock(return_value=poll_resp)
            call_count += 1
            return m

        MockClient.side_effect = client_factory
        client = NotebookLMClient(api_key="test-key")
        result = client.research("Any topic", max_wait_seconds=1)

    assert result is None
```

---

## Codebase Context

### Key Patterns in Use
- **Never raises:** All public methods catch exceptions and return `None`. The non-fiction pipeline handles `None` by calling `LLMClient` instead.
- **Logging on failure:** `logger.warning(...)` on every caught exception — never silent.
- **Separate `httpx.Client` per internal method:** Avoids shared state issues in tests.
- **Polling with deadline:** `time.time() + max_wait_seconds` deadline, 5s sleep between polls.

### Architecture Decisions Affecting This Task
- Requirement 5.3: "IF NotebookLM API is unavailable THEN fall back to LLM-based research synthesis and log a warning; the job SHALL NOT fail."
- `research()` is the only public method. Internal methods `_create_notebook`, `_add_text_source`, `_wait_for_summary` are private.

---

## Handoff from Previous Task

**Files changed by previous task:** `worker/clients/image_client.py`, `tests/unit/test_image_client.py`.
**Decisions made:** Return bytes from ImageClient. Provider SDK isolation pattern confirmed.
**Context for this task:** ImageClient complete. Now build NotebookLM client with graceful fallback pattern.
**Open questions left:** _(none)_

---

## Implementation Steps

1. Create `worker/clients/notebooklm_client.py` — paste template exactly.
2. Create `tests/unit/test_notebooklm_client.py` — paste template exactly.
3. Run: `pytest tests/unit/test_notebooklm_client.py -v` — verify all 3 tests pass.
4. Run: `ruff check worker/clients/notebooklm_client.py` — verify zero lint errors.

---

## Decision Rules

| Scenario | Action |
|----------|--------|
| Any exception in `_create_notebook` | `logger.warning(...)` and return `None` from `research()` |
| Any exception in `_add_text_source` | `logger.warning(...)` and return `None` from `research()` |
| Poll deadline exceeded | `logger.warning("NotebookLM summary timed out after %ds", max_wait_seconds)` and return `None` |
| Successful poll with summary | Return `str(summary)` |
| `summary` field is None or absent in poll response | Continue polling until deadline |

---

## Acceptance Criteria

- [ ] WHEN NotebookLM API is reachable and returns a summary THEN `research()` returns the summary string
- [ ] WHEN the API raises a network error THEN `research()` returns `None` without raising any exception
- [ ] WHEN polling times out THEN `research()` returns `None`
- [ ] WHEN `pytest tests/unit/test_notebooklm_client.py` runs THEN all 3 tests pass

---

## Handoff to Next Task

**Files changed:** _(fill via /task-handoff)_
**Decisions made:** _(fill via /task-handoff)_
**Context for next task:** _(fill via /task-handoff)_
**Open questions:** _(fill via /task-handoff)_
