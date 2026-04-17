---
task: 011
feature: book-generation-engine
status: pending
model: haiku
supervisor: software-cto
agent: software-developer-expert
depends_on: [006, 007, 008, 009, 010]
---

# Task 011: Pipeline Runner and RabbitMQ Worker

## Skills
- .kit/skills/devops/terminal-cli-devops/SKILL.md
- .kit/skills/agents-orchestration/agent-orchestrator/SKILL.md
- .kit/skills/languages/python-patterns/SKILL.md

## Agents
- @software-developer-expert

## Commands
- /task-handoff

> Load the skills, agents, and commands listed above before reading anything else.

---

## Objective

Implement `worker/pipeline/runner.py` that orchestrates all engine stages in sequence, and `worker/main.py` that connects to RabbitMQ, consumes jobs, calls the runner, and emits progress events via a callback. Also implement `app/queue/publisher.py` for job publishing from the FastAPI side.

---

## Files

### Create
| File | Purpose |
|------|---------|
| `worker/pipeline/runner.py` | Full pipeline orchestrator |
| `worker/main.py` | RabbitMQ consumer entrypoint |
| `app/queue/publisher.py` | RabbitMQ job publisher |
| `app/queue/connection.py` | RabbitMQ connection helper |
| `tests/unit/test_runner.py` | Runner unit test with all engines stubbed |

---

## Dependencies

```bash
# aio-pika already in pyproject.toml.
# No new packages.
# Env vars already in .env.example: RABBITMQ_URL
```

---

## Code Templates

### `app/queue/connection.py` (create this file exactly)
```python
"""RabbitMQ connection helper."""
from __future__ import annotations

import aio_pika

QUEUE_NAME = "book_jobs"


async def get_connection(url: str) -> aio_pika.Connection:
    return await aio_pika.connect_robust(url)


async def declare_queue(channel: aio_pika.Channel) -> aio_pika.Queue:
    return await channel.declare_queue(QUEUE_NAME, durable=True)
```

### `app/queue/publisher.py` (create this file exactly)
```python
"""Publish book generation jobs to RabbitMQ."""
from __future__ import annotations

import json

import aio_pika

from app.queue.connection import QUEUE_NAME


async def publish_job(channel: aio_pika.Channel, job_id: str, config: dict) -> None:
    """Publish a job message to the book_jobs queue."""
    payload = json.dumps({"job_id": job_id, "config": config})
    await channel.default_exchange.publish(
        aio_pika.Message(
            body=payload.encode(),
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        ),
        routing_key=QUEUE_NAME,
    )
```

### `worker/pipeline/runner.py` (create this file exactly)
```python
"""Pipeline runner. Orchestrates all engine stages for a single job."""
from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from worker.clients.image_client import ImageClient
from worker.clients.llm_client import LLMClient
from worker.clients.notebooklm_client import NotebookLMClient
from worker.memory.store import FictionMemory, NonFictionMemory
from worker.pipeline.assembly import (
    CoverEngine,
    FinalAssemblyEngine,
    FormattingEngine,
    PackagingEngine,
)
from worker.pipeline.base import JobConfig
from worker.pipeline.fiction_path import (
    CharacterEngine,
    ConceptEngine,
    ConflictEngine,
    EndingEngine,
    StoryMemoryInitEngine,
    StructureEngine,
    ThemeEngine,
)
from worker.pipeline.generation import (
    ChapterGeneratorEngine,
    ContinuityEngine,
    QAEngine,
    StyleEnforcerEngine,
    chapter_passed,
)
from worker.pipeline.non_fiction_path import (
    ContentMapEngine,
    EvidenceEngine,
    FrameworkEngine,
    KnowledgeMemoryInitEngine,
    PromiseEngine,
    ResearchStep,
)
from worker.pipeline.shared_core import (
    AudienceEngine,
    ContentBlueprintSelectorEngine,
    EntryGateEngine,
    IntentEngine,
    PositioningEngine,
)
from worker.services import storage_service

logger = logging.getLogger(__name__)

MAX_CHAPTER_RETRIES = 2


class PipelineRunner:
    """Runs the full book generation pipeline for one job."""

    def __init__(
        self,
        config: JobConfig,
        supabase: Any,
        progress_callback: Callable[[dict], None],
    ) -> None:
        self.config = config
        self.supabase = supabase
        self.progress = progress_callback

        self.llm = LLMClient(
            provider=config.llm_provider,
            model=config.llm_model,
            api_key=config.llm_api_key,
            base_url=config.llm_base_url,
        )
        self.image_client = ImageClient(provider=config.image_provider, api_key=config.image_api_key)
        self.notebooklm = NotebookLMClient(api_key=config.llm_api_key)  # uses Google key

        if config.mode == "fiction":
            self.memory: FictionMemory | NonFictionMemory = FictionMemory(config.job_id)
        else:
            self.memory = NonFictionMemory(config.job_id)

    def run(self) -> None:
        """Execute the full pipeline. Updates Supabase at each stage."""
        ctx: dict[str, Any] = {}

        # --- Shared Core ---
        self._emit("planning", "entry_gate", 0)
        for engine_cls in [EntryGateEngine, IntentEngine, AudienceEngine, PositioningEngine, ContentBlueprintSelectorEngine]:
            engine = engine_cls(llm=self.llm, memory=self.memory, config=self.config)
            ctx = engine.run(ctx)
        self._update_job_status("planning")

        # --- Branch ---
        if ctx["branch"] == "fiction":
            ctx = self._run_fiction_path(ctx)
        else:
            ctx = self._run_non_fiction_path(ctx)

        # --- Chapter Generation Loop ---
        chapters_blueprint = self._get_chapters_blueprint(ctx)
        locked_chapters: list[dict] = []
        total = len(chapters_blueprint)

        for i, ch_brief in enumerate(chapters_blueprint):
            ctx["chapter_index"] = i
            ctx["chapter_brief"] = ch_brief
            ctx["memory_snapshot"] = self.memory.snapshot()

            locked = False
            for attempt in range(MAX_CHAPTER_RETRIES + 1):
                self._emit("generating", f"chapter_{i}", i / total * 100)
                for engine_cls in [ChapterGeneratorEngine, ContinuityEngine, QAEngine, StyleEnforcerEngine]:
                    engine = engine_cls(llm=self.llm, memory=self.memory, config=self.config)
                    ctx = engine.run(ctx)

                if chapter_passed(ctx):
                    self.memory.lock_chapter(i)
                    ch_record = {
                        "index": i,
                        "title": ch_brief.get("title", f"Chapter {i + 1}"),
                        "content": ctx["generated_content"],
                    }
                    locked_chapters.append(ch_record)
                    self._save_chapter(i, ch_record["title"], ctx["generated_content"], "locked")
                    locked = True
                    break
                elif attempt < MAX_CHAPTER_RETRIES:
                    logger.warning("Chapter %d failed QA (attempt %d) — retrying", i, attempt + 1)
                    ctx.pop("generated_content", None)

            if not locked:
                self._save_chapter(i, ch_brief.get("title", f"Chapter {i + 1}"), ctx.get("generated_content", ""), "qa_failed")
                self._update_job_status("paused")
                self._emit("paused", f"chapter_{i}_qa_failed", i / total * 100)
                return

        ctx["locked_chapters"] = locked_chapters

        # --- Assembly ---
        self._emit("assembling", "final_assembly", 90)
        self._update_job_status("assembling")
        for engine_cls in [FinalAssemblyEngine, PackagingEngine]:
            engine = engine_cls(llm=self.llm, memory=self.memory, config=self.config)
            ctx = engine.run(ctx)

        cover_engine = CoverEngine(llm=self.llm, memory=self.memory, config=self.config, image_client=self.image_client)
        ctx = cover_engine.run(ctx)

        formatting_engine = FormattingEngine(llm=self.llm, memory=self.memory, config=self.config)
        ctx = formatting_engine.run(ctx)

        # --- Upload artifacts ---
        bundle_path = storage_service.upload_bytes(
            self.supabase, self.config.job_id, "bundle.zip", ctx["bundle_bytes"], "application/zip"
        )
        download_url = storage_service.get_signed_url(self.supabase, bundle_path)

        self._update_job_status("complete")
        self._emit("complete", "complete", 100, download_url=download_url)
        logger.info("Job %s complete. Bundle: %s", self.config.job_id, bundle_path)

    def _run_fiction_path(self, ctx: dict) -> dict:
        for engine_cls in [ConceptEngine, ThemeEngine, CharacterEngine, ConflictEngine, StructureEngine, EndingEngine, StoryMemoryInitEngine]:
            engine = engine_cls(llm=self.llm, memory=self.memory, config=self.config)
            ctx = engine.run(ctx)
        return ctx

    def _run_non_fiction_path(self, ctx: dict) -> dict:
        assert isinstance(self.memory, NonFictionMemory)
        research = ResearchStep(notebooklm_client=self.notebooklm, llm=self.llm, config=self.config, memory=self.memory)
        ctx = research.run(ctx)
        for engine_cls in [PromiseEngine, FrameworkEngine, ContentMapEngine, EvidenceEngine, KnowledgeMemoryInitEngine]:
            engine = engine_cls(llm=self.llm, memory=self.memory, config=self.config)
            ctx = engine.run(ctx)
        return ctx

    def _get_chapters_blueprint(self, ctx: dict) -> list[dict]:
        """Extract per-chapter briefs from planning context."""
        if ctx.get("branch") == "fiction":
            structure = ctx.get("structure", {})
            chapters = []
            for act in structure.get("acts", []):
                chapters.extend(act.get("chapters", []))
            if not chapters:
                chapters = [{"index": i, "title": f"Chapter {i + 1}", "beats": []} for i in range(self.config.target_chapters)]
            return chapters
        else:
            content_map = ctx.get("content_map", {})
            chapters = content_map.get("chapters", [])
            if not chapters:
                chapters = [{"index": i, "title": f"Chapter {i + 1}", "key_points": []} for i in range(self.config.target_chapters)]
            return chapters

    def _emit(self, status: str, step: str, progress_pct: float, **extra: Any) -> None:
        self.progress({"job_id": self.config.job_id, "status": status, "step": step, "progress": progress_pct, **extra})

    def _update_job_status(self, status: str) -> None:
        self.supabase.table("jobs").update({"status": status}).eq("id", self.config.job_id).execute()

    def _save_chapter(self, index: int, title: str, content: str, status: str) -> None:
        self.supabase.table("chapters").upsert({
            "job_id": self.config.job_id,
            "index": index,
            "content": content,
            "status": status,
            "memory_snapshot": self.memory.snapshot(),
        }).execute()
```

### `worker/main.py` (create this file exactly)
```python
"""RabbitMQ worker entrypoint."""
from __future__ import annotations

import asyncio
import json
import logging
import os

import aio_pika
from supabase import create_client

from app.queue.connection import QUEUE_NAME, declare_queue, get_connection
from worker.pipeline.base import JobConfig
from worker.pipeline.runner import PipelineRunner

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
RABBITMQ_URL = os.environ.get("RABBITMQ_URL", "amqp://guest:guest@localhost/")

# In-memory progress event store for WebSocket broadcast (replaced by Redis pub/sub in production)
_progress_events: dict[str, list[dict]] = {}


def _on_progress(event: dict) -> None:
    job_id = event.get("job_id", "")
    if job_id not in _progress_events:
        _progress_events[job_id] = []
    _progress_events[job_id].append(event)
    logger.info("Progress: %s", event)


async def process_message(message: aio_pika.IncomingMessage) -> None:
    async with message.process():
        body = json.loads(message.body.decode())
        job_id = body["job_id"]
        config_dict = body["config"]
        logger.info("Processing job %s", job_id)
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        config = JobConfig(job_id=job_id, **config_dict)
        runner = PipelineRunner(config=config, supabase=supabase, progress_callback=_on_progress)
        try:
            runner.run()
        except Exception as exc:
            logger.exception("Job %s failed: %s", job_id, exc)
            supabase.table("jobs").update({"status": "failed"}).eq("id", job_id).execute()


async def main() -> None:
    connection = await get_connection(RABBITMQ_URL)
    async with connection:
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=1)
        queue = await declare_queue(channel)
        logger.info("Worker ready. Waiting for jobs on queue '%s'...", QUEUE_NAME)
        await queue.consume(process_message)
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    asyncio.run(main())
```

### `tests/unit/test_runner.py` (create this file exactly)
```python
"""Unit test for PipelineRunner with all engines and external clients stubbed."""
from unittest.mock import MagicMock, patch

import pytest

from worker.pipeline.base import JobConfig
from worker.pipeline.runner import PipelineRunner


def make_config(mode: str = "fiction") -> JobConfig:
    return JobConfig(
        job_id="runner-job-1",
        title="Test Book",
        topic="A test topic",
        mode=mode,
        audience="Testers",
        tone="Neutral",
        target_chapters=2,
        llm_provider="anthropic",
        llm_model="claude-sonnet-4-6",
        llm_api_key="k",
        image_provider="dall-e-3",
        image_api_key="k",
    )


def test_runner_completes_fiction_job_with_stubs():
    config = make_config("fiction")
    mock_supabase = MagicMock()
    mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = None
    mock_supabase.table.return_value.upsert.return_value.execute.return_value = None
    mock_supabase.storage.from_.return_value.upload.return_value = None
    mock_supabase.storage.from_.return_value.create_signed_url.return_value = {"signedURL": "https://example.com/bundle.zip"}

    progress_events = []

    # Stub LLMClient, ImageClient, NotebookLMClient at module level
    with patch("worker.pipeline.runner.LLMClient") as MockLLM, \
         patch("worker.pipeline.runner.ImageClient") as MockImage, \
         patch("worker.pipeline.runner.NotebookLMClient") as MockNLM:

        mock_llm_inst = MagicMock()
        # Return valid JSON for all planning engine calls, then chapter content for generation
        import json
        mock_llm_inst.complete.side_effect = [
            json.dumps({"transformation": "t", "outcome": "o", "reader_state_before": "b", "reader_state_after": "a"}),  # Intent
            json.dumps({"demographics": "d", "expectations": "e", "depth_tolerance": "intermediate", "reading_context": "r"}),  # Audience
            json.dumps({"unique_angle": "u", "market_differentiation": "m", "what_book_avoids": "v"}),  # Positioning
            json.dumps({"hook": "h", "unique_premise": "p", "genre": "g"}),  # Concept
            json.dumps({"central_theme": "ct", "moral_tension": "mt", "meaning": "m"}),  # Theme
            json.dumps({"protagonist": {"name": "Hero", "description": "Brave", "arc": "Growth"}, "antagonist": {"name": "Villain", "description": "Evil", "arc": "Fall"}, "supporting": []}),  # Character
            json.dumps({"internal_conflict": "ic", "external_conflict": "ec", "stakes": "s"}),  # Conflict
            json.dumps({"acts": [{"act": 1, "chapters": [{"index": 0, "title": "Ch1", "beats": []}, {"index": 1, "title": "Ch2", "beats": []}]}]}),  # Structure
            json.dumps({"endings": [{"type": "happy", "description": "Peace", "score": 8}], "selected": 0}),  # Ending
            "Chapter 1 long content here " * 50,  # Chapter 1 generation
            json.dumps({"passed": True, "issues": [], "severity": "none"}),  # Continuity ch1
            json.dumps({"clarity": 8, "pacing": 8, "redundancy": 8, "coherence": 8, "overall": 8, "passed": True, "feedback": ""}),  # QA ch1
            json.dumps({"tone_consistency": 8, "sentence_variation": 8, "readability": 8, "overall": 8, "passed": True, "feedback": ""}),  # Style ch1
            "Chapter 2 long content here " * 50,  # Chapter 2 generation
            json.dumps({"passed": True, "issues": [], "severity": "none"}),  # Continuity ch2
            json.dumps({"clarity": 8, "pacing": 8, "redundancy": 8, "coherence": 8, "overall": 8, "passed": True, "feedback": ""}),  # QA ch2
            json.dumps({"tone_consistency": 8, "sentence_variation": 8, "readability": 8, "overall": 8, "passed": True, "feedback": ""}),  # Style ch2
            json.dumps({"title": "Test Book", "subtitle": "A sub", "description": "Desc", "keywords": ["k1","k2","k3","k4","k5","k6","k7"], "categories": ["Fiction", "Adventure"]}),  # Packaging
            "Cover brief text",  # CoverEngine brief
        ]
        MockLLM.return_value = mock_llm_inst

        mock_image_inst = MagicMock()
        mock_image_inst.generate.return_value = b"fake cover bytes"
        MockImage.return_value = mock_image_inst

        MockNLM.return_value = MagicMock()

        runner = PipelineRunner(config=config, supabase=mock_supabase, progress_callback=lambda e: progress_events.append(e))
        runner.run()

    # Verify job completed
    assert any(e["status"] == "complete" for e in progress_events)
    assert any(e["status"] == "assembling" for e in progress_events)
```

---

## Codebase Context

### Key Code Snippets
```python
# worker/pipeline/generation.py:chapter_passed
def chapter_passed(context: dict[str, Any]) -> bool:
    continuity_ok = context.get("continuity_result", {}).get("passed", True)
    qa_ok = context.get("qa_result", {}).get("passed", False)
    style_ok = context.get("style_result", {}).get("passed", False)
    return continuity_ok and qa_ok and style_ok
```

### Key Patterns in Use
- **Runner owns all external client construction:** LLMClient, ImageClient, NotebookLMClient are built in `__init__`, not inside engines.
- **Progress callback is injected:** Runner never imports WebSocket code — it calls `self.progress(event_dict)`. The worker `main.py` injects the callback.
- **Chapter retry loop:** `for attempt in range(MAX_CHAPTER_RETRIES + 1)` — 3 total attempts (0, 1, 2). If all fail, `_update_job_status("paused")` and return.
- **Supabase called synchronously in runner:** Runner uses the synchronous Supabase client. The async worker wraps it via executor if needed.

---

## Handoff from Previous Task

**Files changed by previous task:** `worker/pipeline/assembly.py`, `worker/services/storage_service.py`, `tests/unit/test_assembly.py`.
**Decisions made:** CoverEngine takes `image_client` as kwarg. Bundle is zip. FormattingEngine produces bytes only.
**Context for this task:** All engines are complete. Now wire them into the runner and worker.
**Open questions left:** _(none)_

---

## Implementation Steps

1. Create `app/queue/connection.py` — paste template exactly.
2. Create `app/queue/publisher.py` — paste template exactly.
3. Create `worker/pipeline/runner.py` — paste template exactly.
4. Create `worker/main.py` — paste template exactly.
5. Create `tests/unit/test_runner.py` — paste template exactly.
6. Run: `pytest tests/unit/test_runner.py -v` — verify test passes.
7. Run: `ruff check worker/pipeline/runner.py worker/main.py` — verify zero lint errors.

---

## Decision Rules

| Scenario | Action |
|----------|--------|
| Chapter fails QA and retries exhausted | Call `_save_chapter(i, ..., "qa_failed")`, call `_update_job_status("paused")`, call `_emit("paused", ...)`, and `return` from `run()` |
| Fiction structure engine returns no chapters | Fall back to `[{"index": i, "title": f"Chapter {i+1}", "beats": []} for i in range(target_chapters)]` |
| Non-fiction content_map returns no chapters | Fall back to `[{"index": i, "title": f"Chapter {i+1}", "key_points": []} for i in range(target_chapters)]` |
| Any engine raises an uncaught exception | Caught in `worker/main.py` `process_message()`, sets job status to `"failed"` |

---

## Acceptance Criteria

- [ ] WHEN `PipelineRunner.run()` completes without failure THEN progress events include `status="assembling"` and `status="complete"`
- [ ] WHEN a chapter fails QA on all retries THEN job status set to `"paused"` and `run()` returns early
- [ ] WHEN `pytest tests/unit/test_runner.py` runs THEN the test passes
- [ ] WHEN `ruff check` runs THEN zero errors

---

## Handoff to Next Task

**Files changed:** _(fill via /task-handoff)_
**Decisions made:** _(fill via /task-handoff)_
**Context for next task:** _(fill via /task-handoff)_
**Open questions:** _(fill via /task-handoff)_

Status: COMPLETE
Completed: 2026-04-17T00:00:00Z
