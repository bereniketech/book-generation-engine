---
task: 007
feature: book-generation-engine
status: pending
model: haiku
supervisor: software-cto
agent: ai-ml-expert
depends_on: [006]
---

# Task 007: Fiction Path Engines (F1–F7)

## Skills
- .kit/skills/data-science-ml/ai-engineer/SKILL.md
- .kit/skills/languages/python-patterns/SKILL.md
- .kit/skills/research-docs/copywriting/SKILL.md

## Agents
- @ai-ml-expert

## Commands
- /task-handoff

> Load the skills, agents, and commands listed above before reading anything else.

---

## Objective

Implement `worker/pipeline/fiction_path.py` containing engines F1 Concept through F7 Story Memory, each calling the LLM and storing results in context and FictionMemory, executed in strict sequence.

---

## Files

### Create
| File | Purpose |
|------|---------|
| `worker/pipeline/fiction_path.py` | F1–F7 engine classes |
| `tests/unit/test_fiction_path.py` | Unit tests with stub LLM |

---

## Dependencies

```bash
# No new packages.
```

---

## Code Templates

### `worker/pipeline/fiction_path.py` (create this file exactly)
```python
"""Fiction pipeline engines F1–F7."""
from __future__ import annotations

import json
import logging
from typing import Any

from worker.memory.store import FictionMemory
from worker.pipeline.base import BaseEngine

logger = logging.getLogger(__name__)

_SYSTEM = "You are an expert fiction development coach. Output JSON only."


def _safe_json(raw: str, fallback_key: str) -> dict[str, Any]:
    try:
        return json.loads(raw)  # type: ignore[no-any-return]
    except json.JSONDecodeError:
        return {fallback_key: raw}


class ConceptEngine(BaseEngine):
    name = "f1_concept"

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        prompt = (
            f"Book title: '{self.config.title}'. Topic: '{self.config.topic}'.\n"
            'Generate a fiction concept as JSON: {"hook": "...", "unique_premise": "...", "genre": "..."}'
        )
        raw = self.llm.complete(prompt, _SYSTEM)
        concept = _safe_json(raw, "hook")
        context["concept"] = concept
        self.memory.update("concept", concept)
        return context


class ThemeEngine(BaseEngine):
    name = "f2_theme"

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        concept = context.get("concept", {})
        prompt = (
            f"Concept: {json.dumps(concept)}.\n"
            'Define theme as JSON: {"central_theme": "...", "moral_tension": "...", "meaning": "..."}'
        )
        raw = self.llm.complete(prompt, _SYSTEM)
        theme = _safe_json(raw, "central_theme")
        context["theme"] = theme
        self.memory.update("theme", theme)
        return context


class CharacterEngine(BaseEngine):
    name = "f3_character"

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        assert isinstance(self.memory, FictionMemory), "CharacterEngine requires FictionMemory"
        prompt = (
            f"Concept: {json.dumps(context.get('concept', {}))}. Theme: {json.dumps(context.get('theme', {}))}.\n"
            'Define characters as JSON: {"protagonist": {"name":"...","description":"...","arc":"..."}, '
            '"antagonist": {"name":"...","description":"...","arc":"..."}, "supporting": []}'
        )
        raw = self.llm.complete(prompt, _SYSTEM)
        chars = _safe_json(raw, "protagonist")
        if "protagonist" in chars and isinstance(chars["protagonist"], dict):
            p = chars["protagonist"]
            self.memory.add_character(p.get("name", "Protagonist"), "protagonist", p.get("description", ""), p.get("arc", ""))
        if "antagonist" in chars and isinstance(chars["antagonist"], dict):
            a = chars["antagonist"]
            self.memory.add_character(a.get("name", "Antagonist"), "antagonist", a.get("description", ""), a.get("arc", ""))
        context["characters"] = chars
        return context


class ConflictEngine(BaseEngine):
    name = "f4_conflict"

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        prompt = (
            f"Characters: {json.dumps(context.get('characters', {}))}.\n"
            'Map conflict as JSON: {"internal_conflict": "...", "external_conflict": "...", "stakes": "..."}'
        )
        raw = self.llm.complete(prompt, _SYSTEM)
        conflict = _safe_json(raw, "internal_conflict")
        context["conflict"] = conflict
        self.memory.update("conflict", conflict)
        return context


class StructureEngine(BaseEngine):
    name = "f5_structure"

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        prompt = (
            f"Conflict: {json.dumps(context.get('conflict', {}))}. Target chapters: {self.config.target_chapters}.\n"
            f'Create a beat-based outline as JSON: {{"acts": [{{"act": 1, "chapters": [{{"index": 0, "title": "...", "beats": ["..."]}}]}}]}}'
        )
        raw = self.llm.complete(prompt, _SYSTEM)
        structure = _safe_json(raw, "acts")
        context["structure"] = structure
        self.memory.update("structure", structure)
        return context


class EndingEngine(BaseEngine):
    name = "f6_ending"

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        prompt = (
            f"Structure: {json.dumps(context.get('structure', {}))}. Theme: {json.dumps(context.get('theme', {}))}.\n"
            'Generate 3 ending options as JSON: {"endings": [{"type": "...", "description": "...", "score": 0-10}], "selected": 0}'
        )
        raw = self.llm.complete(prompt, _SYSTEM)
        ending = _safe_json(raw, "endings")
        context["ending"] = ending
        self.memory.update("ending", ending)
        return context


class StoryMemoryInitEngine(BaseEngine):
    name = "f7_story_memory"

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        assert isinstance(self.memory, FictionMemory), "StoryMemoryInitEngine requires FictionMemory"
        # Consolidate all fiction planning into memory
        for key in ("concept", "theme", "conflict", "structure", "ending"):
            if key in context:
                self.memory.update(key, context[key])
        context["fiction_memory_initialised"] = True
        context["memory_snapshot"] = self.memory.snapshot()
        logger.info("[StoryMemory] Initialised for job %s", self.config.job_id)
        return context
```

### `tests/unit/test_fiction_path.py` (create this file exactly)
```python
"""Unit tests for fiction path engines F1–F7."""
import json
from unittest.mock import MagicMock

import pytest

from worker.memory.store import FictionMemory
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


def make_config() -> JobConfig:
    return JobConfig(
        job_id="fiction-job-1",
        title="The Iron Path",
        topic="A warrior's redemption",
        mode="fiction",
        audience="Adults 25-45",
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


def test_concept_engine_stores_concept_in_context_and_memory():
    config = make_config()
    mem = FictionMemory(config.job_id)
    concept_json = json.dumps({"hook": "A warrior lost his sword", "unique_premise": "Swords are souls", "genre": "Epic fantasy"})
    engine = ConceptEngine(llm=stub_llm(concept_json), memory=mem, config=config)
    ctx = engine.run({})
    assert ctx["concept"]["hook"] == "A warrior lost his sword"
    assert mem.get("concept")["hook"] == "A warrior lost his sword"


def test_concept_engine_handles_non_json():
    config = make_config()
    engine = ConceptEngine(llm=stub_llm("not json"), memory=FictionMemory(config.job_id), config=config)
    ctx = engine.run({})
    assert "hook" in ctx["concept"]


def test_character_engine_adds_protagonist_to_memory():
    config = make_config()
    mem = FictionMemory(config.job_id)
    char_json = json.dumps({
        "protagonist": {"name": "Aric", "description": "A fallen knight", "arc": "Redemption"},
        "antagonist": {"name": "Vex", "description": "A dark sorcerer", "arc": "Corruption"},
        "supporting": [],
    })
    engine = CharacterEngine(llm=stub_llm(char_json), memory=mem, config=config)
    ctx = engine.run({"concept": {}, "theme": {}})
    characters = mem.get("characters")
    assert "Aric" in characters
    assert characters["Aric"]["role"] == "protagonist"


def test_story_memory_init_sets_initialised_flag():
    config = make_config()
    mem = FictionMemory(config.job_id)
    engine = StoryMemoryInitEngine(llm=stub_llm(""), memory=mem, config=config)
    ctx = engine.run({"concept": {"hook": "x"}, "theme": {}, "conflict": {}, "structure": {}, "ending": {}})
    assert ctx["fiction_memory_initialised"] is True
    assert "memory_snapshot" in ctx


def test_structure_engine_stores_structure():
    config = make_config()
    mem = FictionMemory(config.job_id)
    structure_json = json.dumps({"acts": [{"act": 1, "chapters": [{"index": 0, "title": "Begin", "beats": ["Hero wakes"]}]}]})
    engine = StructureEngine(llm=stub_llm(structure_json), memory=mem, config=config)
    ctx = engine.run({"conflict": {}})
    assert "acts" in ctx["structure"]
```

---

## Codebase Context

### Key Code Snippets
```python
# worker/pipeline/base.py — BaseEngine interface
class BaseEngine(ABC):
    name: str = "base"
    def __init__(self, llm: LLMClient, memory: MemoryStore, config: JobConfig) -> None: ...
    @abstractmethod
    def run(self, context: dict[str, Any]) -> dict[str, Any]: ...
```

### Key Patterns in Use
- **`_safe_json(raw, fallback_key)`:** All engines use this helper to avoid crashes on malformed LLM output.
- **FictionMemory type assertion:** Engines that call FictionMemory-specific methods (`add_character`, `lock_chapter`) assert `isinstance(self.memory, FictionMemory)`.
- **Context is cumulative:** Each engine reads prior keys from context and adds its own. Never delete prior keys.

### Architecture Decisions Affecting This Task
- F7 StoryMemoryInitEngine consolidates all planning into memory and produces `context["memory_snapshot"]` — the runner persists this to Supabase.
- Requirement 4.3: Empty/invalid LLM response → retry once, then fail with `fiction_planning_failed`. The runner handles retries; individual engines just return their result (or a fallback dict).

---

## Handoff from Previous Task

**Files changed by previous task:** `worker/pipeline/base.py`, `worker/pipeline/shared_core.py`, `tests/unit/test_shared_core.py`.
**Decisions made:** `_safe_json` fallback pattern. Context dict as pipeline bus. Memory mirrors context.
**Context for this task:** BaseEngine and JobConfig exist. Now build F1–F7 on top of them.
**Open questions left:** _(none)_

---

## Implementation Steps

1. Create `worker/pipeline/fiction_path.py` — paste template exactly.
2. Create `tests/unit/test_fiction_path.py` — paste template exactly.
3. Run: `pytest tests/unit/test_fiction_path.py -v` — verify all 5 tests pass.
4. Run: `ruff check worker/pipeline/fiction_path.py` — verify zero lint errors.

---

## Decision Rules

| Scenario | Action |
|----------|--------|
| LLM returns non-JSON for any engine | `_safe_json(raw, fallback_key)` wraps raw in `{fallback_key: raw}` |
| CharacterEngine: protagonist missing from LLM response | Use `"Protagonist"` as default name |
| StoryMemoryInitEngine: key not in context | Skip that key silently (use `if key in context`) |

---

## Acceptance Criteria

- [ ] WHEN ConceptEngine runs THEN `context["concept"]` and `memory.get("concept")` match
- [ ] WHEN CharacterEngine runs with valid JSON THEN protagonist is in `FictionMemory.get("characters")`
- [ ] WHEN StoryMemoryInitEngine runs THEN `context["fiction_memory_initialised"] == True`
- [ ] WHEN any engine receives non-JSON LLM response THEN no exception is raised
- [ ] WHEN `pytest tests/unit/test_fiction_path.py` runs THEN all 5 tests pass

---

## Handoff to Next Task

**Files changed:** _(fill via /task-handoff)_
**Decisions made:** _(fill via /task-handoff)_
**Context for next task:** _(fill via /task-handoff)_
**Open questions:** _(fill via /task-handoff)_

Status: COMPLETE
Completed: 2026-04-17T00:00:00Z
