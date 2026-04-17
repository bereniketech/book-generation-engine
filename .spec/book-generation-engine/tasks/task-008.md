---
task: 008
feature: book-generation-engine
status: pending
model: haiku
supervisor: software-cto
agent: ai-ml-expert
depends_on: [006, 004]
---

# Task 008: Non-Fiction Path Engines (N1–N5) + NotebookLM Integration

## Skills
- .kit/skills/data-science-ml/ai-engineer/SKILL.md
- .kit/skills/ai-platform/notebooklm/SKILL.md
- .kit/skills/languages/python-patterns/SKILL.md
- .kit/skills/research-docs/research-information-retreival/SKILL.md
- .kit/skills/research-docs/deep-research/SKILL.md

## Agents
- @ai-ml-expert

## Commands
- /task-handoff

> Load the skills, agents, and commands listed above before reading anything else.

---

## Objective

Implement `worker/pipeline/non_fiction_path.py` containing the NotebookLM research step and engines N1 Promise through N5 Knowledge Memory, with graceful LLM fallback when NotebookLM is unavailable.

---

## Files

### Create
| File | Purpose |
|------|---------|
| `worker/pipeline/non_fiction_path.py` | Research step + N1–N5 engines |
| `tests/unit/test_non_fiction_path.py` | Unit tests for happy path + NotebookLM fallback |

---

## Dependencies

```bash
# No new packages.
```

---

## Code Templates

### `worker/pipeline/non_fiction_path.py` (create this file exactly)
```python
"""Non-fiction pipeline engines N1–N5, preceded by NotebookLM deep research."""
from __future__ import annotations

import json
import logging
from typing import Any

from worker.clients.notebooklm_client import NotebookLMClient
from worker.memory.store import NonFictionMemory
from worker.pipeline.base import BaseEngine

logger = logging.getLogger(__name__)

_SYSTEM = "You are an expert non-fiction book architect. Output JSON only."


def _safe_json(raw: str, fallback_key: str) -> dict[str, Any]:
    try:
        return json.loads(raw)  # type: ignore[no-any-return]
    except json.JSONDecodeError:
        return {fallback_key: raw}


class ResearchStep:
    """Not a BaseEngine — runs before engines. Calls NotebookLM and stores research summary."""

    def __init__(self, notebooklm_client: NotebookLMClient, llm: Any, config: Any, memory: NonFictionMemory) -> None:
        self.notebooklm = notebooklm_client
        self.llm = llm
        self.config = config
        self.memory = memory

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        logger.info("[Research] Starting NotebookLM deep research for job %s", self.config.job_id)
        # Primary: NotebookLM deep research (--mode deep)
        # Equivalent CLI: notebooklm source add-research "<topic>" --mode deep --no-wait
        # then: notebooklm research wait --import-all
        # then: notebooklm generate report --format briefing-doc
        # Uses NotebookLM's deep research feature for multi-source synthesis,
        # competitive intel, literature review, and trend spotting before generation.
        summary = self.notebooklm.deep_research(self.config.topic, max_wait_seconds=300)
        if summary is None:
            logger.warning("[Research] NotebookLM unavailable — falling back to LLM synthesis for job %s", self.config.job_id)
            # Fallback: multi-angle LLM synthesis following research-information-retreival protocol:
            # 1) broad orienting pass, 2) sub-topic deep dives, 3) cross-reference + synthesize
            angles = [
                f"Key concepts, definitions, and foundational frameworks for: {self.config.topic}",
                f"Evidence, case studies, and expert perspectives on: {self.config.topic}",
                f"Current trends, debates, and practical applications of: {self.config.topic}",
            ]
            parts = []
            for angle in angles:
                parts.append(self.llm.complete(angle, "You are a research analyst. Be specific, cite examples, no filler."))
            summary = "\n\n---\n\n".join(parts)
        self.memory.update("research_summary", summary)
        context["research_summary"] = summary
        return context


class PromiseEngine(BaseEngine):
    name = "n1_promise"

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        research = context.get("research_summary", "")
        prompt = (
            f"Book: '{self.config.title}'. Research: {research[:2000]}. Audience: '{self.config.audience}'.\n"
            'Define the reader promise as JSON: {"transformation": "...", "specific_outcome": "...", "time_frame": "..."}'
        )
        raw = self.llm.complete(prompt, _SYSTEM)
        promise = _safe_json(raw, "transformation")
        context["promise"] = promise
        self.memory.update("promise", promise)
        return context


class FrameworkEngine(BaseEngine):
    name = "n2_framework"

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        prompt = (
            f"Promise: {json.dumps(context.get('promise', {}))}. Research: {str(context.get('research_summary', ''))[:1000]}.\n"
            'Define the step-by-step framework as JSON: {"framework_name": "...", "steps": [{"step": 1, "name": "...", "description": "..."}]}'
        )
        raw = self.llm.complete(prompt, _SYSTEM)
        framework = _safe_json(raw, "framework_name")
        context["framework"] = framework
        self.memory.update("framework", framework)
        return context


class ContentMapEngine(BaseEngine):
    name = "n3_content_map"

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        prompt = (
            f"Framework: {json.dumps(context.get('framework', {}))}. Target chapters: {self.config.target_chapters}.\n"
            f'Create chapter breakdown as JSON: {{"chapters": [{{"index": 0, "title": "...", "key_points": ["..."], "framework_step": 1}}]}}'
        )
        raw = self.llm.complete(prompt, _SYSTEM)
        content_map = _safe_json(raw, "chapters")
        context["content_map"] = content_map
        self.memory.update("content_map", content_map)
        return context


class EvidenceEngine(BaseEngine):
    name = "n4_evidence"

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        assert isinstance(self.memory, NonFictionMemory), "EvidenceEngine requires NonFictionMemory"
        research = context.get("research_summary", "")
        prompt = (
            f"Research summary: {research[:2000]}. Framework: {json.dumps(context.get('framework', {}))}.\n"
            'Extract 5-10 pieces of evidence as JSON: {"evidence": [{"source": "...", "summary": "...", "chapter_index": 0}]}'
        )
        raw = self.llm.complete(prompt, _SYSTEM)
        evidence_data = _safe_json(raw, "evidence")
        evidence_list = evidence_data.get("evidence", [])
        if isinstance(evidence_list, list):
            for item in evidence_list:
                if isinstance(item, dict):
                    self.memory.add_evidence(item.get("source", ""), item.get("summary", ""))
        context["evidence"] = evidence_data
        return context


class KnowledgeMemoryInitEngine(BaseEngine):
    name = "n5_knowledge_memory"

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        assert isinstance(self.memory, NonFictionMemory), "KnowledgeMemoryInitEngine requires NonFictionMemory"
        for key in ("promise", "framework", "content_map", "evidence", "research_summary"):
            if key in context:
                self.memory.update(key, context[key])
        context["non_fiction_memory_initialised"] = True
        context["memory_snapshot"] = self.memory.snapshot()
        logger.info("[KnowledgeMemory] Initialised for job %s", self.config.job_id)
        return context
```

### `tests/unit/test_non_fiction_path.py` (create this file exactly)
```python
"""Unit tests for non-fiction path engines."""
import json
from unittest.mock import MagicMock

import pytest

from worker.clients.notebooklm_client import NotebookLMClient
from worker.memory.store import NonFictionMemory
from worker.pipeline.base import JobConfig
from worker.pipeline.non_fiction_path import (
    ContentMapEngine,
    EvidenceEngine,
    FrameworkEngine,
    KnowledgeMemoryInitEngine,
    PromiseEngine,
    ResearchStep,
)


def make_config() -> JobConfig:
    return JobConfig(
        job_id="nf-job-1",
        title="The Stoic Leader",
        topic="Stoicism applied to modern leadership",
        mode="non_fiction",
        audience="Executives",
        tone="Authoritative",
        target_chapters=10,
        llm_provider="anthropic",
        llm_model="claude-sonnet-4-6",
        llm_api_key="k",
        image_provider="dall-e-3",
        image_api_key="k",
    )


def stub_llm(response: str) -> MagicMock:
    m = MagicMock()
    m.complete.return_value = response
    return m


def test_research_step_uses_notebooklm_summary():
    config = make_config()
    mem = NonFictionMemory(config.job_id)
    mock_nlm = MagicMock(spec=NotebookLMClient)
    mock_nlm.research.return_value = "Rich research summary from NotebookLM."
    step = ResearchStep(notebooklm_client=mock_nlm, llm=stub_llm(""), config=config, memory=mem)
    ctx = step.run({})
    assert ctx["research_summary"] == "Rich research summary from NotebookLM."
    assert mem.get("research_summary") == "Rich research summary from NotebookLM."


def test_research_step_falls_back_to_llm_when_notebooklm_returns_none():
    config = make_config()
    mem = NonFictionMemory(config.job_id)
    mock_nlm = MagicMock(spec=NotebookLMClient)
    mock_nlm.research.return_value = None
    llm = stub_llm("LLM synthesised research.")
    step = ResearchStep(notebooklm_client=mock_nlm, llm=llm, config=config, memory=mem)
    ctx = step.run({})
    assert ctx["research_summary"] == "LLM synthesised research."
    llm.complete.assert_called_once()


def test_promise_engine_stores_promise():
    config = make_config()
    mem = NonFictionMemory(config.job_id)
    promise_json = json.dumps({"transformation": "Calm leader", "specific_outcome": "Better decisions", "time_frame": "90 days"})
    engine = PromiseEngine(llm=stub_llm(promise_json), memory=mem, config=config)
    ctx = engine.run({"research_summary": "summary"})
    assert ctx["promise"]["transformation"] == "Calm leader"
    assert mem.get("promise")["transformation"] == "Calm leader"


def test_evidence_engine_adds_evidence_to_memory():
    config = make_config()
    mem = NonFictionMemory(config.job_id)
    evidence_json = json.dumps({"evidence": [
        {"source": "Harvard 2021", "summary": "Leaders who meditate are 30% more effective", "chapter_index": 2}
    ]})
    engine = EvidenceEngine(llm=stub_llm(evidence_json), memory=mem, config=config)
    engine.run({"research_summary": "", "framework": {}})
    assert len(mem.get("evidence_used")) == 1
    assert mem.get("evidence_used")[0]["source"] == "Harvard 2021"


def test_knowledge_memory_init_sets_flag():
    config = make_config()
    mem = NonFictionMemory(config.job_id)
    engine = KnowledgeMemoryInitEngine(llm=stub_llm(""), memory=mem, config=config)
    ctx = engine.run({"promise": {}, "framework": {}, "content_map": {}, "evidence": {}, "research_summary": "x"})
    assert ctx["non_fiction_memory_initialised"] is True
    assert "memory_snapshot" in ctx
```

---

## Codebase Context

### Key Code Snippets
```python
# worker/memory/store.py — NonFictionMemory methods
class NonFictionMemory(MemoryStore):
    def add_evidence(self, source: str, summary: str) -> None: ...
    def add_concept(self, concept: str) -> None: ...
    def is_concept_used(self, concept: str) -> bool: ...
    def lock_chapter(self, chapter_index: int) -> None: ...
```

### Key Patterns in Use
- **ResearchStep is not a BaseEngine:** It takes `NotebookLMClient` as a dependency, not an LLM. The runner calls it before the engine sequence.
- **Graceful fallback:** If `notebooklm.research()` returns `None`, call `llm.complete()` with a research synthesis prompt. Never raise.
- **`_safe_json` reused from fiction path:** Copy the exact function into this module (do not import across pipeline modules).

---

## Handoff from Previous Task

**Files changed by previous task:** `worker/pipeline/fiction_path.py`, `tests/unit/test_fiction_path.py`.
**Decisions made:** `_safe_json` fallback pattern for all engines. FictionMemory type assertions.
**Context for this task:** F1–F7 done. Now build N1–N5 with the same patterns plus NotebookLM research.
**Open questions left:** _(none)_

---

## Implementation Steps

1. Create `worker/pipeline/non_fiction_path.py` — paste template exactly.
2. Create `tests/unit/test_non_fiction_path.py` — paste template exactly.
3. Run: `pytest tests/unit/test_non_fiction_path.py -v` — verify all 5 tests pass.
4. Run: `ruff check worker/pipeline/non_fiction_path.py` — verify zero lint errors.

---

## Decision Rules

| Scenario | Action |
|----------|--------|
| `notebooklm.research()` returns `None` | Call `llm.complete(research_synthesis_prompt)` and store result as `research_summary` |
| EvidenceEngine: `evidence` key absent in LLM JSON | Set `evidence_list = []` (no evidence added to memory) |
| Any engine: LLM returns non-JSON | `_safe_json(raw, fallback_key)` wraps raw string |

---

## Acceptance Criteria

- [ ] WHEN NotebookLM returns a summary THEN `context["research_summary"]` equals that summary
- [ ] WHEN NotebookLM returns `None` THEN LLM is called for research synthesis and result stored
- [ ] WHEN EvidenceEngine runs THEN each evidence item is added to `NonFictionMemory.evidence_used`
- [ ] WHEN KnowledgeMemoryInitEngine runs THEN `context["non_fiction_memory_initialised"] == True`
- [ ] WHEN `pytest tests/unit/test_non_fiction_path.py` runs THEN all 5 tests pass

---

## Handoff to Next Task

**Files changed:** _(fill via /task-handoff)_
**Decisions made:** _(fill via /task-handoff)_
**Context for next task:** _(fill via /task-handoff)_
**Open questions:** _(fill via /task-handoff)_

Status: COMPLETE
Completed: 2026-04-17T00:00:00Z
