---
task: 002
feature: book-generation-engine
status: pending
model: haiku
supervisor: software-cto
agent: ai-ml-expert
depends_on: [001]
---

# Task 002: LLMClient Abstraction (All Providers)

## Skills
- .kit/skills/data-science-ml/ai-engineer/SKILL.md
- .kit/skills/languages/python-patterns/SKILL.md
- .kit/rules/python/patterns.md
- .kit/rules/python/testing.md

## Agents
- @ai-ml-expert

## Commands
- /task-handoff

> Load the skills, agents, and commands listed above before reading anything else. Do not load context not listed here.

---

## Objective

Implement the `LLMClient` abstraction in `worker/clients/llm_client.py` that routes to Anthropic, OpenAI, Google Gemini, Ollama, or any OpenAI-compatible API, with retry logic on rate-limit errors.

---

## Files

### Create
| File | Purpose |
|------|---------|
| `worker/clients/llm_client.py` | LLMClient + exception classes |
| `worker/clients/exceptions.py` | UnsupportedProviderError, ProviderRateLimitError |
| `tests/unit/test_llm_client.py` | Unit tests for all 5 provider routes + retry logic |

---

## Dependencies

```bash
# All deps already in pyproject.toml from task-001.
# No new packages.
# No new env vars beyond those in .env.example.
```

---

## API Contracts

_(none — internal class, not an HTTP endpoint)_

---

## Code Templates

### `worker/clients/exceptions.py` (create this file exactly)
```python
class UnsupportedProviderError(ValueError):
    """Raised at LLMClient construction when provider name is not recognised."""
    pass


class ProviderRateLimitError(RuntimeError):
    """Raised after max retries are exhausted on a provider rate-limit response."""
    pass
```

### `worker/clients/llm_client.py` (create this file exactly)
```python
"""Provider-agnostic LLM client. No engine imports a provider SDK directly."""
from __future__ import annotations

import asyncio
import time
from typing import Literal

import anthropic
import google.generativeai as genai
import httpx
import openai

from worker.clients.exceptions import ProviderRateLimitError, UnsupportedProviderError

SUPPORTED_PROVIDERS = frozenset({"anthropic", "openai", "google", "ollama", "openai-compatible"})
MAX_RETRIES = 3
BACKOFF_BASE = 0.5  # seconds


class LLMClient:
    """Single interface for all LLM providers. Constructed once per job."""

    def __init__(
        self,
        provider: Literal["anthropic", "openai", "google", "ollama", "openai-compatible"],
        model: str,
        api_key: str,
        base_url: str | None = None,
    ) -> None:
        if provider not in SUPPORTED_PROVIDERS:
            raise UnsupportedProviderError(
                f"Provider '{provider}' is not supported. Choose from: {sorted(SUPPORTED_PROVIDERS)}"
            )
        self.provider = provider
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self._client = self._build_client()

    def _build_client(self) -> object:
        if self.provider == "anthropic":
            return anthropic.Anthropic(api_key=self.api_key)
        if self.provider in ("openai", "openai-compatible"):
            kwargs: dict = {"api_key": self.api_key}
            if self.base_url:
                kwargs["base_url"] = self.base_url
            return openai.OpenAI(**kwargs)
        if self.provider == "ollama":
            return openai.OpenAI(
                api_key="ollama",
                base_url=self.base_url or "http://localhost:11434/v1",
            )
        if self.provider == "google":
            genai.configure(api_key=self.api_key)
            return genai.GenerativeModel(self.model)
        raise UnsupportedProviderError(self.provider)  # unreachable but satisfies mypy

    def complete(self, prompt: str, system_prompt: str = "") -> str:
        """Synchronous completion. Retries on rate-limit up to MAX_RETRIES times."""
        for attempt in range(MAX_RETRIES):
            try:
                return self._dispatch_sync(prompt, system_prompt)
            except (openai.RateLimitError, anthropic.RateLimitError) as exc:
                if attempt == MAX_RETRIES - 1:
                    raise ProviderRateLimitError(
                        f"Provider '{self.provider}' rate-limited after {MAX_RETRIES} retries."
                    ) from exc
                time.sleep(BACKOFF_BASE * (2**attempt))
        raise ProviderRateLimitError("Unreachable — loop exhausted.")

    async def acomplete(self, prompt: str, system_prompt: str = "") -> str:
        """Async completion. Retries on rate-limit up to MAX_RETRIES times."""
        for attempt in range(MAX_RETRIES):
            try:
                return await self._dispatch_async(prompt, system_prompt)
            except (openai.RateLimitError, anthropic.RateLimitError) as exc:
                if attempt == MAX_RETRIES - 1:
                    raise ProviderRateLimitError(
                        f"Provider '{self.provider}' rate-limited after {MAX_RETRIES} retries."
                    ) from exc
                await asyncio.sleep(BACKOFF_BASE * (2**attempt))
        raise ProviderRateLimitError("Unreachable — loop exhausted.")

    def _dispatch_sync(self, prompt: str, system_prompt: str) -> str:
        if self.provider == "anthropic":
            client: anthropic.Anthropic = self._client  # type: ignore[assignment]
            message = client.messages.create(
                model=self.model,
                max_tokens=8192,
                system=system_prompt,
                messages=[{"role": "user", "content": prompt}],
            )
            return message.content[0].text  # type: ignore[union-attr]
        if self.provider in ("openai", "openai-compatible", "ollama"):
            client_oa: openai.OpenAI = self._client  # type: ignore[assignment]
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            response = client_oa.chat.completions.create(
                model=self.model,
                messages=messages,  # type: ignore[arg-type]
            )
            return response.choices[0].message.content or ""
        if self.provider == "google":
            gm: genai.GenerativeModel = self._client  # type: ignore[assignment]
            response = gm.generate_content(
                f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
            )
            return response.text
        raise UnsupportedProviderError(self.provider)

    async def _dispatch_async(self, prompt: str, system_prompt: str) -> str:
        # Run sync dispatch in executor to avoid blocking the event loop.
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._dispatch_sync, prompt, system_prompt)
```

### `tests/unit/test_llm_client.py` (create this file exactly)
```python
"""Unit tests for LLMClient. All provider SDK calls are mocked."""
from unittest.mock import MagicMock, patch

import pytest

from worker.clients.exceptions import ProviderRateLimitError, UnsupportedProviderError
from worker.clients.llm_client import LLMClient


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------

def test_unsupported_provider_raises_at_construction():
    with pytest.raises(UnsupportedProviderError, match="badprovider"):
        LLMClient(provider="badprovider", model="x", api_key="k")  # type: ignore[arg-type]


def test_supported_providers_construct_without_error():
    with patch("worker.clients.llm_client.anthropic.Anthropic"):
        LLMClient(provider="anthropic", model="claude-sonnet-4-6", api_key="test-key")

    with patch("worker.clients.llm_client.openai.OpenAI"):
        LLMClient(provider="openai", model="gpt-4o", api_key="test-key")
        LLMClient(provider="openai-compatible", model="some-model", api_key="k", base_url="http://x")
        LLMClient(provider="ollama", model="llama3", api_key="k")

    with patch("worker.clients.llm_client.genai.configure"), \
         patch("worker.clients.llm_client.genai.GenerativeModel"):
        LLMClient(provider="google", model="gemini-pro", api_key="k")


# ---------------------------------------------------------------------------
# Anthropic completion
# ---------------------------------------------------------------------------

def test_anthropic_complete_returns_text():
    mock_client = MagicMock()
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text="Generated text")]
    )
    with patch("worker.clients.llm_client.anthropic.Anthropic", return_value=mock_client):
        llm = LLMClient(provider="anthropic", model="claude-sonnet-4-6", api_key="k")
    result = llm.complete("Hello", "You are helpful")
    assert result == "Generated text"
    mock_client.messages.create.assert_called_once()


# ---------------------------------------------------------------------------
# OpenAI completion
# ---------------------------------------------------------------------------

def test_openai_complete_returns_text():
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content="OpenAI response"))]
    )
    with patch("worker.clients.llm_client.openai.OpenAI", return_value=mock_client):
        llm = LLMClient(provider="openai", model="gpt-4o", api_key="k")
    result = llm.complete("Hello")
    assert result == "OpenAI response"


# ---------------------------------------------------------------------------
# Google completion
# ---------------------------------------------------------------------------

def test_google_complete_returns_text():
    mock_model = MagicMock()
    mock_model.generate_content.return_value = MagicMock(text="Gemini response")
    with patch("worker.clients.llm_client.genai.configure"), \
         patch("worker.clients.llm_client.genai.GenerativeModel", return_value=mock_model):
        llm = LLMClient(provider="google", model="gemini-pro", api_key="k")
    result = llm.complete("Hello", "System")
    assert result == "Gemini response"
    mock_model.generate_content.assert_called_with("System\n\nHello")


# ---------------------------------------------------------------------------
# Ollama (OpenAI-compatible local)
# ---------------------------------------------------------------------------

def test_ollama_uses_local_base_url_by_default():
    with patch("worker.clients.llm_client.openai.OpenAI") as MockOpenAI:
        LLMClient(provider="ollama", model="llama3", api_key="k")
    call_kwargs = MockOpenAI.call_args[1]
    assert "localhost:11434" in call_kwargs["base_url"]


# ---------------------------------------------------------------------------
# Rate-limit retry
# ---------------------------------------------------------------------------

def test_rate_limit_retries_then_raises():
    import openai as _openai

    mock_client = MagicMock()
    mock_client.messages.create.side_effect = _openai.RateLimitError(
        "rate limited", response=MagicMock(status_code=429), body={}
    )
    with patch("worker.clients.llm_client.anthropic.Anthropic", return_value=mock_client), \
         patch("worker.clients.llm_client.time.sleep"):
        llm = LLMClient(provider="anthropic", model="claude-sonnet-4-6", api_key="k")
        with pytest.raises(ProviderRateLimitError):
            llm.complete("test")

    assert mock_client.messages.create.call_count == 3  # MAX_RETRIES
```

---

## Codebase Context

### Key Code Snippets
```python
# worker/clients/exceptions.py — exceptions to import in llm_client.py
class UnsupportedProviderError(ValueError): ...
class ProviderRateLimitError(RuntimeError): ...
```

### Key Patterns in Use
- **Provider SDK isolation:** Only `llm_client.py` imports `anthropic`, `openai`, `google.generativeai`. No other file imports these SDKs.
- **Retry with exponential backoff:** `BACKOFF_BASE * (2 ** attempt)` — 0.5s, 1.0s, 2.0s. Max 3 attempts.
- **UnsupportedProviderError at construction:** Fail fast; never at call time.
- **Async wraps sync:** `acomplete` uses `run_in_executor` for async-safe usage in FastAPI.

### Architecture Decisions Affecting This Task
- All engines call `llm.complete(prompt, system_prompt)` — the interface is fixed. Do not add parameters.
- `base_url` is required for `openai-compatible`; optional for `ollama` (defaults to localhost).

---

## Handoff from Previous Task

**Files changed by previous task:** `pyproject.toml`, `docker-compose.yml`, `Makefile`, `app/main.py`, `supabase/migrations/001_initial_schema.sql`, all `__init__.py` files.
**Decisions made:** Python 3.12, Pydantic v2, async-first FastAPI, Supabase for state.
**Context for this task:** Task-001 created the project structure. Venv and deps are installed.
**Open questions left:** _(none)_

---

## Implementation Steps

1. Create `worker/clients/exceptions.py` — paste template exactly.
2. Create `worker/clients/llm_client.py` — paste template exactly.
3. Create `tests/unit/test_llm_client.py` — paste template exactly.
4. Run: `pytest tests/unit/test_llm_client.py -v` — verify all tests pass.
5. Run: `ruff check worker/clients/` — verify zero lint errors.
6. Run: `mypy worker/clients/llm_client.py` — verify zero type errors.

---

## Test Cases

_(Embedded in `tests/unit/test_llm_client.py` above — 8 test functions covering all 5 providers + retry + unsupported provider.)_

---

## Decision Rules

| Scenario | Action |
|----------|--------|
| Provider name not in SUPPORTED_PROVIDERS | Raise `UnsupportedProviderError(f"Provider '{provider}' is not supported. Choose from: {sorted(SUPPORTED_PROVIDERS)}")` at `__init__` |
| `openai.RateLimitError` or `anthropic.RateLimitError` on attempt < MAX_RETRIES | Sleep `BACKOFF_BASE * (2 ** attempt)` seconds and retry |
| Rate-limit error on attempt == MAX_RETRIES - 1 | Raise `ProviderRateLimitError(f"Provider '{self.provider}' rate-limited after {MAX_RETRIES} retries.")` |
| Google provider: `system_prompt` is non-empty | Prepend to prompt as `f"{system_prompt}\n\n{prompt}"` |
| OpenAI/compatible: `system_prompt` is empty string | Do not add a system message to the messages list |

---

## Acceptance Criteria

- [ ] WHEN `LLMClient(provider="badprovider", ...)` is called THEN `UnsupportedProviderError` is raised immediately
- [ ] WHEN Anthropic rate-limits 3 times THEN `ProviderRateLimitError` is raised after 3 attempts
- [ ] WHEN each of the 5 supported providers is constructed THEN no error is raised
- [ ] WHEN `complete()` is called with Anthropic provider THEN `client.messages.create()` is called and text returned
- [ ] WHEN `ruff check worker/clients/` runs THEN zero lint errors
- [ ] WHEN `mypy worker/clients/llm_client.py` runs THEN zero type errors

---

## Handoff to Next Task

**Files changed:** _(fill via /task-handoff)_
**Decisions made:** _(fill via /task-handoff)_
**Context for next task:** _(fill via /task-handoff)_
**Open questions:** _(fill via /task-handoff)_
