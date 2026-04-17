---
task: 009
feature: book-generation-engine
status: pending
model: haiku
supervisor: software-cto
agent: ai-ml-expert
depends_on: [007, 008]
---

# Task 009: Chapter Generator, Continuity, QA, and Style Enforcer Engines

## Skills
- .kit/skills/data-science-ml/ai-engineer/SKILL.md
- .kit/skills/languages/python-patterns/SKILL.md
- .kit/skills/research-docs/beautiful-prose/SKILL.md
- .kit/skills/research-docs/avoid-ai-writing/SKILL.md
- .kit/skills/research-docs/document-content-writing-editing/SKILL.md

## Agents
- @ai-ml-expert
- @technical-writer-expert

## Commands
- /task-handoff

> Load the skills, agents, and commands listed above before reading anything else.

---

## Objective

Implement `worker/pipeline/generation.py` with 4 engine classes for per-chapter generation: Chapter Generator, Continuity Engine, QA Engine, and Style Enforcer. The runner calls them in sequence for each chapter; engines return a result dict (not WebSocket events — the runner handles progress emission).

---

## Files

### Create
| File | Purpose |
|------|---------|
| `worker/pipeline/generation.py` | 4 chapter generation engines |
| `tests/unit/test_generation.py` | Unit tests: happy path, QA fail, retry exhaustion |

---

## Dependencies

```bash
# No new packages.
```

---

## Code Templates

### `worker/pipeline/generation.py` (create this file exactly)
```python
"""Per-chapter generation engines."""
from __future__ import annotations

import json
import logging
from typing import Any, Literal

from worker.pipeline.base import BaseEngine

logger = logging.getLogger(__name__)

_GENERATION_SYSTEM = (
    "You are a professional book author writing timeless, forceful prose.\n"
    "Rules (enforce strictly):\n"
    "- Write clean, exact, muscular sentences. Vary length aggressively. Short sentences hit hard.\n"
    "- Use concrete nouns, strong verbs. No adverbs where a better verb works.\n"
    "- No filler transitions: 'In today's world', 'That said', 'Moreover', 'Ultimately', 'At its core'.\n"
    "- No AI-isms: 'leverage', 'robust', 'seamless', 'cutting-edge', 'delve', 'tapestry', 'testament to'.\n"
    "- No em dashes as pivots. No 'It's not X, it's Y' reversals.\n"
    "- No therapy language. No meta-commentary ('In this chapter...').\n"
    "- Open with substance. Close cleanly without restating the point.\n"
    "- Every paragraph must advance meaning. Cut any sentence that merely repeats the previous.\n"
    "Write as if truth needs no permission."
)
_QA_SYSTEM = "You are a rigorous book editor. Output JSON only."


class ChapterGeneratorEngine(BaseEngine):
    """Generates raw chapter content from blueprint + memory context."""
    name = "chapter_generator"

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        chapter_index: int = context["chapter_index"]
        chapter_brief: dict = context.get("chapter_brief", {})
        memory_snapshot: dict = context.get("memory_snapshot", {})

        prompt = (
            f"Book: '{self.config.title}'. Mode: {self.config.mode}.\n"
            f"Chapter {chapter_index + 1} brief: {json.dumps(chapter_brief)}.\n"
            f"Memory context (do not repeat what is already introduced): {json.dumps(memory_snapshot)}\n"
            f"Audience: {self.config.audience}. Tone: {self.config.tone}.\n"
            "Write the complete chapter content. Minimum 800 words. Do not include chapter number in output."
        )
        content = self.llm.complete(prompt, _GENERATION_SYSTEM)
        context["generated_content"] = content
        return context


class ContinuityEngine(BaseEngine):
    """Checks generated chapter for continuity against memory state."""
    name = "continuity_engine"

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        content: str = context.get("generated_content", "")
        memory_snapshot: dict = context.get("memory_snapshot", {})

        prompt = (
            f"Chapter content:\n{content[:3000]}\n\n"
            f"Memory state: {json.dumps(memory_snapshot)}\n\n"
            "Check for continuity issues. Output JSON: "
            '{"passed": true|false, "issues": ["..."], "severity": "none|minor|major"}'
        )
        raw = self.llm.complete(prompt, _QA_SYSTEM)
        try:
            result = json.loads(raw)
        except json.JSONDecodeError:
            result = {"passed": True, "issues": [], "severity": "none"}
        context["continuity_result"] = result
        return context


class QAEngine(BaseEngine):
    """Scores the chapter on clarity, pacing, redundancy, coherence."""
    name = "qa_engine"
    PASS_THRESHOLD = 6  # Score 1-10; must be >= 6 to pass

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        content: str = context.get("generated_content", "")
        prompt = (
            f"Chapter content:\n{content[:3000]}\n\n"
            "Score this chapter 1-10 on: clarity, pacing, redundancy (10=no redundancy), coherence. "
            "Output JSON: "
            '{"clarity": 7, "pacing": 7, "redundancy": 8, "coherence": 7, "overall": 7, "passed": true, "feedback": "..."}'
        )
        raw = self.llm.complete(prompt, _QA_SYSTEM)
        try:
            scores = json.loads(raw)
        except json.JSONDecodeError:
            scores = {"clarity": 7, "pacing": 7, "redundancy": 7, "coherence": 7, "overall": 7, "passed": True, "feedback": ""}
        # Override passed based on threshold
        scores["passed"] = int(scores.get("overall", 0)) >= self.PASS_THRESHOLD
        context["qa_result"] = scores
        return context


class StyleEnforcerEngine(BaseEngine):
    """Checks tone consistency, sentence variation, readability."""
    name = "style_enforcer"
    PASS_THRESHOLD = 6

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        content: str = context.get("generated_content", "")
        prompt = (
            f"Target tone: '{self.config.tone}'. Audience: '{self.config.audience}'.\n"
            f"Chapter content:\n{content[:3000]}\n\n"
            "Evaluate style. Check for AI-writing patterns (filler transitions like 'Moreover'/'That said'/"
            "'In today's world', hollow intensifiers, AI-isms like 'leverage'/'robust'/'seamless'/'delve', "
            "em-dash pivot constructions, therapy language, meta-commentary). "
            "Output JSON: "
            '{"tone_consistency": 8, "sentence_variation": 7, "readability": 8, "ai_isms_detected": 0, "overall": 7, "passed": true, "feedback": "..."}'
        )
        raw = self.llm.complete(prompt, _QA_SYSTEM)
        try:
            scores = json.loads(raw)
        except json.JSONDecodeError:
            scores = {"tone_consistency": 7, "sentence_variation": 7, "readability": 7, "overall": 7, "passed": True, "feedback": ""}
        scores["passed"] = int(scores.get("overall", 0)) >= self.PASS_THRESHOLD
        context["style_result"] = scores
        return context


def chapter_passed(context: dict[str, Any]) -> bool:
    """Return True if continuity, QA, and style all passed."""
    continuity_ok = context.get("continuity_result", {}).get("passed", True)
    qa_ok = context.get("qa_result", {}).get("passed", False)
    style_ok = context.get("style_result", {}).get("passed", False)
    return continuity_ok and qa_ok and style_ok
```

### `tests/unit/test_generation.py` (create this file exactly)
```python
"""Unit tests for chapter generation engines."""
import json
from unittest.mock import MagicMock

import pytest

from worker.memory.store import FictionMemory
from worker.pipeline.base import JobConfig
from worker.pipeline.generation import (
    ChapterGeneratorEngine,
    ContinuityEngine,
    QAEngine,
    StyleEnforcerEngine,
    chapter_passed,
)


def make_config() -> JobConfig:
    return JobConfig(
        job_id="gen-job-1",
        title="The Iron Path",
        topic="Warrior redemption",
        mode="fiction",
        audience="Adults",
        tone="Epic",
        target_chapters=12,
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


def test_chapter_generator_stores_content():
    config = make_config()
    mem = FictionMemory(config.job_id)
    engine = ChapterGeneratorEngine(llm=stub_llm("Chapter one content goes here..."), memory=mem, config=config)
    ctx = engine.run({"chapter_index": 0, "chapter_brief": {"title": "The Beginning"}, "memory_snapshot": {}})
    assert ctx["generated_content"] == "Chapter one content goes here..."


def test_qa_engine_passes_when_score_above_threshold():
    config = make_config()
    mem = FictionMemory(config.job_id)
    qa_json = json.dumps({"clarity": 8, "pacing": 7, "redundancy": 8, "coherence": 8, "overall": 8, "passed": True, "feedback": "Good"})
    engine = QAEngine(llm=stub_llm(qa_json), memory=mem, config=config)
    ctx = engine.run({"generated_content": "some content"})
    assert ctx["qa_result"]["passed"] is True


def test_qa_engine_fails_when_score_below_threshold():
    config = make_config()
    mem = FictionMemory(config.job_id)
    qa_json = json.dumps({"clarity": 4, "pacing": 4, "redundancy": 4, "coherence": 4, "overall": 4, "passed": True, "feedback": "Poor"})
    engine = QAEngine(llm=stub_llm(qa_json), memory=mem, config=config)
    ctx = engine.run({"generated_content": "weak content"})
    assert ctx["qa_result"]["passed"] is False  # QAEngine overrides based on threshold


def test_qa_engine_handles_non_json():
    config = make_config()
    engine = QAEngine(llm=stub_llm("not json"), memory=FictionMemory(config.job_id), config=config)
    ctx = engine.run({"generated_content": "content"})
    assert ctx["qa_result"]["passed"] is True  # fallback defaults pass


def test_chapter_passed_returns_true_when_all_pass():
    ctx = {
        "continuity_result": {"passed": True},
        "qa_result": {"passed": True},
        "style_result": {"passed": True},
    }
    assert chapter_passed(ctx) is True


def test_chapter_passed_returns_false_when_qa_fails():
    ctx = {
        "continuity_result": {"passed": True},
        "qa_result": {"passed": False},
        "style_result": {"passed": True},
    }
    assert chapter_passed(ctx) is False


def test_style_enforcer_passes_with_good_scores():
    config = make_config()
    style_json = json.dumps({"tone_consistency": 8, "sentence_variation": 7, "readability": 8, "overall": 8, "passed": True, "feedback": ""})
    engine = StyleEnforcerEngine(llm=stub_llm(style_json), memory=FictionMemory(config.job_id), config=config)
    ctx = engine.run({"generated_content": "content"})
    assert ctx["style_result"]["passed"] is True
```

---

## Codebase Context

### Key Patterns in Use
- **`chapter_passed(context)` helper:** The runner calls this after all 4 engines run for a chapter. If False, it retries up to 2 times, then sets chapter `qa_failed`.
- **QAEngine overrides `passed` field:** Even if LLM returns `"passed": true`, QAEngine recalculates based on `overall >= PASS_THRESHOLD`. This prevents LLM hallucinating a passing score.
- **Content truncated to 3000 chars in prompts:** LLM calls for QA/style/continuity truncate chapter content to keep token cost low.

### Architecture Decisions Affecting This Task
- Engines emit no WebSocket events — they return updated context dicts. The runner (`task-011`) handles progress broadcasting.
- Runner retries: if `chapter_passed(ctx) == False` after first run, runner clears `generated_content` and re-runs all 4 engines (max 2 retries). Engines themselves are stateless and don't know about retry count.

---

## Handoff from Previous Task

**Files changed by previous task:** `worker/pipeline/non_fiction_path.py`, `tests/unit/test_non_fiction_path.py`.
**Decisions made:** ResearchStep + N1–N5 pattern. Graceful NotebookLM fallback confirmed.
**Context for this task:** Planning engines (shared core + fiction/non-fiction paths) are all done. Now build the generation layer.
**Open questions left:** _(none)_

---

## Implementation Steps

1. Create `worker/pipeline/generation.py` — paste template exactly.
2. Create `tests/unit/test_generation.py` — paste template exactly.
3. Run: `pytest tests/unit/test_generation.py -v` — verify all 7 tests pass.
4. Run: `ruff check worker/pipeline/generation.py` — verify zero lint errors.

---

## Decision Rules

| Scenario | Action |
|----------|--------|
| LLM returns non-JSON for QAEngine | Use fallback dict with `overall=7, passed=True` |
| LLM returns non-JSON for StyleEnforcerEngine | Use fallback dict with `overall=7, passed=True` |
| LLM returns non-JSON for ContinuityEngine | Use fallback dict with `passed=True, issues=[], severity="none"` |
| QA `overall` score < 6 | Set `scores["passed"] = False` regardless of LLM's `passed` field |
| Style `overall` score < 6 | Set `scores["passed"] = False` regardless of LLM's `passed` field |

---

## Acceptance Criteria

- [ ] WHEN ChapterGeneratorEngine runs THEN `context["generated_content"]` is set to LLM output
- [ ] WHEN QAEngine receives `overall=4` THEN `qa_result["passed"] == False`
- [ ] WHEN QAEngine receives non-JSON THEN fallback dict used, no exception raised
- [ ] WHEN `chapter_passed()` is called with all three passing THEN returns `True`
- [ ] WHEN `chapter_passed()` is called with QA failing THEN returns `False`
- [ ] WHEN `pytest tests/unit/test_generation.py` runs THEN all 7 tests pass

---

## Handoff to Next Task

**Files changed:** _(fill via /task-handoff)_
**Decisions made:** _(fill via /task-handoff)_
**Context for next task:** _(fill via /task-handoff)_
**Open questions:** _(fill via /task-handoff)_

Status: COMPLETE
Completed: 2026-04-17T00:00:00Z
