---
task: 018
feature: book-generation-engine
status: pending
model: haiku
supervisor: software-cto
agent: devops-infra-expert
depends_on: [017]
---

# Task 018: End-to-End Test and CI Pipeline

## Skills
- .kit/skills/testing-quality/tdd-workflow/SKILL.md
- .kit/skills/devops/terminal-cli-devops/SKILL.md

## Agents
- @devops-infra-expert

## Commands
- /task-handoff

> Load the skills, agents, and commands listed above before reading anything else.

---

## Objective

Write an end-to-end integration test (fiction job via stub LLM → all artifacts present) and create the GitHub Actions CI workflow (lint → type-check → unit tests → e2e test → Docker build).

---

## Files

### Create
| File | Purpose |
|------|---------|
| `tests/e2e/test_full_pipeline.py` | E2E test: submit fiction job, wait for complete, verify artifacts |
| `.github/workflows/ci.yml` | GitHub Actions CI pipeline |
| `Dockerfile` | Production Docker image for FastAPI |
| `Dockerfile.worker` | Production Docker image for worker |

---

## Dependencies

```bash
# No new Python packages.
# GitHub Actions uses ubuntu-latest runner.
```

---

## Code Templates

### `tests/e2e/test_full_pipeline.py` (create this file exactly)
```python
"""End-to-end test for the book generation pipeline.

Uses a stub LLM provider (ollama pointing to a test fixture server)
or mocks PipelineRunner for isolated testing.
This test verifies that:
1. A job can be submitted and consumed by the worker.
2. All expected artifacts exist after completion.
3. Job status transitions correctly.

Run with: pytest tests/e2e/ -v --timeout=300
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from worker.pipeline.base import JobConfig
from worker.pipeline.runner import PipelineRunner


def make_config() -> JobConfig:
    return JobConfig(
        job_id="e2e-test-job-1",
        title="The Stoic Path",
        topic="Applying stoic philosophy to modern leadership",
        mode="fiction",
        audience="Executives",
        tone="Authoritative",
        target_chapters=2,
        llm_provider="anthropic",
        llm_model="claude-sonnet-4-6",
        llm_api_key="test-key",
        image_provider="dall-e-3",
        image_api_key="img-key",
        notification_email="test@example.com",
    )


def _llm_responses() -> list[str]:
    """Ordered stub LLM responses covering all pipeline stages for a 2-chapter fiction book."""
    planning = [
        json.dumps({"transformation": "t", "outcome": "o", "reader_state_before": "b", "reader_state_after": "a"}),
        json.dumps({"demographics": "d", "expectations": "e", "depth_tolerance": "intermediate", "reading_context": "r"}),
        json.dumps({"unique_angle": "u", "market_differentiation": "m", "what_book_avoids": "v"}),
        json.dumps({"hook": "h", "unique_premise": "p", "genre": "g"}),
        json.dumps({"central_theme": "ct", "moral_tension": "mt", "meaning": "m"}),
        json.dumps({"protagonist": {"name": "Marcus", "description": "Stoic leader", "arc": "Growth"}, "antagonist": {"name": "Tyrant", "description": "Corrupt", "arc": "Fall"}, "supporting": []}),
        json.dumps({"internal_conflict": "ic", "external_conflict": "ec", "stakes": "s"}),
        json.dumps({"acts": [{"act": 1, "chapters": [{"index": 0, "title": "Chapter One", "beats": []}, {"index": 1, "title": "Chapter Two", "beats": []}]}]}),
        json.dumps({"endings": [{"type": "triumphant", "description": "Marcus prevails", "score": 9}], "selected": 0}),
    ]
    generation = [
        "Chapter One content. " * 100,  # ch0 generation
        json.dumps({"passed": True, "issues": [], "severity": "none"}),  # continuity ch0
        json.dumps({"clarity": 8, "pacing": 8, "redundancy": 8, "coherence": 8, "overall": 8, "passed": True, "feedback": ""}),  # QA ch0
        json.dumps({"tone_consistency": 8, "sentence_variation": 8, "readability": 8, "overall": 8, "passed": True, "feedback": ""}),  # style ch0
        "Chapter Two content. " * 100,  # ch1 generation
        json.dumps({"passed": True, "issues": [], "severity": "none"}),  # continuity ch1
        json.dumps({"clarity": 8, "pacing": 8, "redundancy": 8, "coherence": 8, "overall": 8, "passed": True, "feedback": ""}),  # QA ch1
        json.dumps({"tone_consistency": 8, "sentence_variation": 8, "readability": 8, "overall": 8, "passed": True, "feedback": ""}),  # style ch1
    ]
    assembly = [
        json.dumps({"title": "The Stoic Path", "subtitle": "A Leadership Journey", "description": "An epic tale of stoic leadership.", "keywords": ["stoic","leader","philosophy","growth","wisdom","strength","resilience"], "categories": ["Business", "Self-Help"]}),
        "Dark navy cover with gold lettering, minimalist design.",  # cover brief
    ]
    return planning + generation + assembly


def test_full_fiction_pipeline_completes_with_all_artifacts():
    config = make_config()
    mock_supabase = MagicMock()
    mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = None
    mock_supabase.table.return_value.upsert.return_value.execute.return_value = None
    mock_supabase.storage.from_.return_value.upload.return_value = None
    mock_supabase.storage.from_.return_value.create_signed_url.return_value = {
        "signedURL": "https://supabase.example.com/storage/v1/sign/book-artifacts/e2e-test-job-1/bundle.zip?token=xxx"
    }

    progress_events: list[dict] = []
    llm_responses = _llm_responses()

    with patch("worker.pipeline.runner.LLMClient") as MockLLM, \
         patch("worker.pipeline.runner.ImageClient") as MockImage, \
         patch("worker.pipeline.runner.NotebookLMClient") as MockNLM:

        mock_llm_inst = MagicMock()
        mock_llm_inst.complete.side_effect = llm_responses
        MockLLM.return_value = mock_llm_inst

        mock_image_inst = MagicMock()
        mock_image_inst.generate.return_value = b"fake cover image bytes"
        MockImage.return_value = mock_image_inst

        MockNLM.return_value = MagicMock()

        runner = PipelineRunner(
            config=config,
            supabase=mock_supabase,
            progress_callback=lambda e: progress_events.append(e),
        )
        runner.run()

    # Verify all pipeline stages were reached
    statuses = [e.get("status") for e in progress_events]
    assert "assembling" in statuses, f"Expected 'assembling' in progress events: {statuses}"
    assert "complete" in statuses, f"Expected 'complete' in progress events: {statuses}"

    # Verify storage upload was called (bundle uploaded)
    assert mock_supabase.storage.from_.return_value.upload.called, "Expected bundle to be uploaded to storage"

    # Verify download URL in complete event
    complete_events = [e for e in progress_events if e.get("status") == "complete"]
    assert len(complete_events) >= 1
    assert "download_url" in complete_events[0]
    assert "supabase.example.com" in complete_events[0]["download_url"]

    # Verify job status was set to 'complete'
    update_calls = mock_supabase.table.return_value.update.call_args_list
    status_values = [call[0][0].get("status") for call in update_calls if call[0][0].get("status")]
    assert "complete" in status_values, f"Expected 'complete' status update: {status_values}"

    # Verify chapter records were saved (2 chapters upserted)
    upsert_calls = mock_supabase.table.return_value.upsert.call_args_list
    chapter_upserts = [c for c in upsert_calls if c[0][0].get("job_id") == "e2e-test-job-1"]
    assert len(chapter_upserts) >= 2, f"Expected at least 2 chapter upserts, got {len(chapter_upserts)}"
```

### `.github/workflows/ci.yml` (create this file exactly)
```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    name: Lint, Type-Check, Tests
    runs-on: ubuntu-latest

    services:
      rabbitmq:
        image: rabbitmq:3.13-alpine
        ports:
          - 5672:5672
        options: >-
          --health-cmd "rabbitmq-diagnostics ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python 3.12
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e ".[dev]"

      - name: Lint (ruff)
        run: ruff check app/ worker/ tests/

      - name: Type check (mypy)
        run: mypy app/ worker/ --ignore-missing-imports

      - name: Unit tests
        run: pytest tests/unit/ -v --cov=app --cov=worker --cov-report=xml

      - name: E2E test
        run: pytest tests/e2e/ -v --timeout=120
        env:
          SUPABASE_URL: "http://localhost:54321"
          SUPABASE_SERVICE_ROLE_KEY: "test-key"
          RABBITMQ_URL: "amqp://guest:guest@localhost/"

      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          file: ./coverage.xml
        continue-on-error: true

  build:
    name: Docker Build
    runs-on: ubuntu-latest
    needs: test

    steps:
      - uses: actions/checkout@v4

      - name: Build FastAPI image
        run: docker build -f Dockerfile -t book-engine-api:ci .

      - name: Build Worker image
        run: docker build -f Dockerfile.worker -t book-engine-worker:ci .
```

### `Dockerfile` (create this file exactly)
```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir -e .

COPY app/ ./app/

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### `Dockerfile.worker` (create this file exactly)
```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir -e .

COPY worker/ ./worker/
COPY app/queue/ ./app/queue/
COPY app/config.py ./app/config.py
COPY app/__init__.py ./app/__init__.py

CMD ["python", "-m", "worker.main"]
```

---

## Codebase Context

### Key Code Snippets
```python
# worker/pipeline/runner.py — PipelineRunner constructor
class PipelineRunner:
    def __init__(self, config: JobConfig, supabase: Any, progress_callback: Callable[[dict], None]) -> None: ...
    def run(self) -> None: ...
```

### Key Patterns in Use
- **E2E test patches at runner module level:** `patch("worker.pipeline.runner.LLMClient")` — intercepts client construction inside PipelineRunner.
- **Ordered `side_effect` list:** All LLM calls must be pre-loaded in the exact order the pipeline calls them. Adding an engine adds to this list.
- **CI runs on ubuntu-latest:** RabbitMQ provided as a service container. Supabase mocked in E2E test (no real Supabase in CI).
- **Docker multi-stage not needed:** Simple single-stage `python:3.12-slim` for both images.

### Architecture Decisions Affecting This Task
- CI does not run the frontend build — that is a separate concern. Backend CI only.
- `--timeout=120` for E2E test via `pytest-timeout` (add to dev deps if not present).

---

## Handoff from Previous Task

**Files changed by previous task:** `frontend/components/ExportView.tsx`, `frontend/app/jobs/[id]/export/page.tsx`.
**Decisions made:** Browser-native `<a download>` for bundle download. Yellow warning for non-complete export.
**Context for this task:** Frontend is complete. Now add E2E test and CI pipeline.
**Open questions left:** _(none)_

---

## Implementation Steps

1. Edit `pyproject.toml` to add `"pytest-timeout>=4.2.0"` to `[project.optional-dependencies] dev`.
2. Create `tests/e2e/__init__.py` — empty file.
3. Create `tests/e2e/test_full_pipeline.py` — paste template exactly.
4. Create `.github/workflows/ci.yml` — paste template exactly (create `.github/workflows/` directory first).
5. Create `Dockerfile` — paste template exactly.
6. Create `Dockerfile.worker` — paste template exactly.
7. Run: `pytest tests/e2e/test_full_pipeline.py -v --timeout=120` — verify test passes.
8. Run: `docker build -f Dockerfile -t book-engine-api:ci .` — verify image builds.
9. Run: `docker build -f Dockerfile.worker -t book-engine-worker:ci .` — verify image builds.

---

## Decision Rules

| Scenario | Action |
|----------|--------|
| E2E test LLM side_effect list runs out | `StopIteration` raised — add missing response to `_llm_responses()` list |
| `pytest-timeout` not installed | Add to pyproject.toml dev deps and `pip install -e ".[dev]"` |
| Docker build fails on `ebooklib` | Pin `ebooklib==0.18` explicitly in `pyproject.toml` |

---

## Acceptance Criteria

- [ ] WHEN `pytest tests/e2e/test_full_pipeline.py -v` runs THEN test passes with green output
- [ ] WHEN `docker build -f Dockerfile` runs THEN image builds without error
- [ ] WHEN `docker build -f Dockerfile.worker` runs THEN image builds without error
- [ ] WHEN `pytest tests/unit/ -v` runs THEN all unit tests pass (regression check)
- [ ] `.github/workflows/ci.yml` exists with lint, type-check, unit test, e2e test, and Docker build jobs

---

## Handoff to Next Task

**Files changed:** _(fill via /task-handoff)_
**Decisions made:** _(fill via /task-handoff)_
**Context for next task:** Spec complete — all 18 tasks done. Reply "start" to begin execution with task-001.
**Open questions:** _(none)_

Status: COMPLETE
Completed: 2026-04-17T00:00:00Z
