---
task: 005
feature: book-generation-engine
status: complete
model: haiku
supervisor: software-cto
agent: software-developer-expert
depends_on: [001]
---

# Task 005: MemoryStore (Fiction + Non-Fiction Variants)

## Skills
- .kit/skills/languages/python-patterns/SKILL.md
- .kit/rules/python/patterns.md

## Agents
- @software-developer-expert

## Commands
- /task-handoff

> Load the skills, agents, and commands listed above before reading anything else. Do not load context not listed here.

---

## Objective

Implement `worker/memory/store.py` with `MemoryStore` base class and `FictionMemory` / `NonFictionMemory` subclasses that track generation state and produce JSON-serialisable snapshots for Supabase persistence.

---

## Files

### Create
| File | Purpose |
|------|---------|
| `worker/memory/store.py` | MemoryStore base + FictionMemory + NonFictionMemory |
| `tests/unit/test_memory_store.py` | Unit tests for all memory types |

---

## Dependencies

```bash
# No new packages — stdlib only (typing, dataclasses).
```

---

## API Contracts

_(none — internal classes)_

---

## Code Templates

### `worker/memory/store.py` (create this file exactly)
```python
"""In-memory state tracking for generation engines.

Each engine calls update() to record what it produced.
snapshot() returns the full state as a JSON-serialisable dict for Supabase persistence.
"""
from __future__ import annotations

from typing import Any, Literal


class MemoryStore:
    """Base memory store. Provides key-value storage + JSON snapshot."""

    def __init__(self, job_id: str, mode: Literal["fiction", "non_fiction"]) -> None:
        self.job_id = job_id
        self.mode = mode
        self._data: dict[str, Any] = {}

    def update(self, key: str, value: Any) -> None:
        """Store or overwrite a key in memory."""
        self._data[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """Retrieve a value by key. Returns default if key not found."""
        return self._data.get(key, default)

    def snapshot(self) -> dict[str, Any]:
        """Return a JSON-serialisable copy of all memory state."""
        import copy
        return {"job_id": self.job_id, "mode": self.mode, "data": copy.deepcopy(self._data)}


class FictionMemory(MemoryStore):
    """Tracks story-specific state: characters, timeline, world rules, locked chapters."""

    def __init__(self, job_id: str) -> None:
        super().__init__(job_id, "fiction")
        self._data.update({
            "characters": {},     # name -> {role, description, arc}
            "timeline": [],       # list of {chapter_index, event}
            "world_rules": [],    # list of established world facts
            "locked_chapters": [], # list of chapter indexes that are locked
            "concept": None,
            "theme": None,
            "conflict": None,
            "structure": None,
            "ending": None,
        })

    def add_character(self, name: str, role: str, description: str, arc: str) -> None:
        """Register a character. Overwrites if name already exists."""
        self._data["characters"][name] = {
            "role": role,
            "description": description,
            "arc": arc,
        }

    def add_timeline_event(self, chapter_index: int, event: str) -> None:
        """Append a story event tied to a chapter."""
        self._data["timeline"].append({"chapter_index": chapter_index, "event": event})

    def add_world_rule(self, rule: str) -> None:
        """Add an established world rule (e.g. 'magic requires spoken words')."""
        if rule not in self._data["world_rules"]:
            self._data["world_rules"].append(rule)

    def lock_chapter(self, chapter_index: int) -> None:
        """Mark a chapter as locked."""
        if chapter_index not in self._data["locked_chapters"]:
            self._data["locked_chapters"].append(chapter_index)


class NonFictionMemory(MemoryStore):
    """Tracks non-fiction state: concepts introduced, frameworks, repetition control."""

    def __init__(self, job_id: str) -> None:
        super().__init__(job_id, "non_fiction")
        self._data.update({
            "concepts_introduced": [],    # list of concept strings
            "frameworks_used": [],        # list of framework names
            "evidence_used": [],          # list of {source, summary}
            "locked_chapters": [],        # list of chapter indexes
            "promise": None,
            "framework": None,
            "content_map": None,
            "research_summary": None,     # from NotebookLM or LLM fallback
        })

    def add_concept(self, concept: str) -> None:
        """Track a concept introduced in any chapter to prevent repetition."""
        if concept not in self._data["concepts_introduced"]:
            self._data["concepts_introduced"].append(concept)

    def add_framework(self, framework_name: str) -> None:
        """Track a framework introduced to prevent re-introduction."""
        if framework_name not in self._data["frameworks_used"]:
            self._data["frameworks_used"].append(framework_name)

    def add_evidence(self, source: str, summary: str) -> None:
        """Record a piece of evidence (case study, statistic) as used."""
        self._data["evidence_used"].append({"source": source, "summary": summary})

    def lock_chapter(self, chapter_index: int) -> None:
        """Mark a chapter as locked."""
        if chapter_index not in self._data["locked_chapters"]:
            self._data["locked_chapters"].append(chapter_index)

    def is_concept_used(self, concept: str) -> bool:
        """Return True if this concept was already introduced in a prior chapter."""
        return concept in self._data["concepts_introduced"]
```

### `tests/unit/test_memory_store.py` (create this file exactly)
```python
"""Unit tests for MemoryStore, FictionMemory, NonFictionMemory."""
import pytest

from worker.memory.store import FictionMemory, MemoryStore, NonFictionMemory


# ---------------------------------------------------------------------------
# MemoryStore base
# ---------------------------------------------------------------------------

def test_base_store_update_and_get():
    store = MemoryStore(job_id="job-1", mode="fiction")
    store.update("key1", "value1")
    assert store.get("key1") == "value1"


def test_base_store_get_default():
    store = MemoryStore(job_id="job-1", mode="fiction")
    assert store.get("missing", default="fallback") == "fallback"


def test_base_store_snapshot_is_copy():
    store = MemoryStore(job_id="job-1", mode="fiction")
    store.update("x", [1, 2, 3])
    snap = store.snapshot()
    snap["data"]["x"].append(99)
    # Original should be unmodified
    assert store.get("x") == [1, 2, 3]


def test_base_store_snapshot_contains_job_id_and_mode():
    store = MemoryStore(job_id="job-42", mode="non_fiction")
    snap = store.snapshot()
    assert snap["job_id"] == "job-42"
    assert snap["mode"] == "non_fiction"


# ---------------------------------------------------------------------------
# FictionMemory
# ---------------------------------------------------------------------------

def test_fiction_memory_add_character():
    mem = FictionMemory(job_id="j1")
    mem.add_character("Alice", role="protagonist", description="Brave woman", arc="Hero journey")
    chars = mem.get("characters")
    assert "Alice" in chars
    assert chars["Alice"]["role"] == "protagonist"


def test_fiction_memory_add_world_rule_no_duplicates():
    mem = FictionMemory(job_id="j1")
    mem.add_world_rule("Magic costs energy")
    mem.add_world_rule("Magic costs energy")
    assert mem.get("world_rules").count("Magic costs energy") == 1


def test_fiction_memory_lock_chapter():
    mem = FictionMemory(job_id="j1")
    mem.lock_chapter(0)
    mem.lock_chapter(0)  # duplicate — should not double-add
    assert mem.get("locked_chapters") == [0]


def test_fiction_memory_timeline_ordering():
    mem = FictionMemory(job_id="j1")
    mem.add_timeline_event(0, "Hero meets mentor")
    mem.add_timeline_event(1, "Hero faces first trial")
    timeline = mem.get("timeline")
    assert len(timeline) == 2
    assert timeline[0]["chapter_index"] == 0


# ---------------------------------------------------------------------------
# NonFictionMemory
# ---------------------------------------------------------------------------

def test_non_fiction_memory_add_concept_no_duplicates():
    mem = NonFictionMemory(job_id="j2")
    mem.add_concept("Growth mindset")
    mem.add_concept("Growth mindset")
    assert mem.get("concepts_introduced").count("Growth mindset") == 1


def test_non_fiction_memory_is_concept_used():
    mem = NonFictionMemory(job_id="j2")
    mem.add_concept("Stoicism")
    assert mem.is_concept_used("Stoicism") is True
    assert mem.is_concept_used("Epicureanism") is False


def test_non_fiction_memory_add_evidence():
    mem = NonFictionMemory(job_id="j2")
    mem.add_evidence("Harvard Study 2020", "Daily habits improve focus by 40%")
    evidence = mem.get("evidence_used")
    assert len(evidence) == 1
    assert evidence[0]["source"] == "Harvard Study 2020"


def test_non_fiction_memory_snapshot_includes_research_summary():
    mem = NonFictionMemory(job_id="j2")
    mem.update("research_summary", "Detailed research on leadership.")
    snap = mem.snapshot()
    assert snap["data"]["research_summary"] == "Detailed research on leadership."
```

---

## Codebase Context

### Key Patterns in Use
- **Snapshot is deep copy:** Mutating the returned snapshot dict must not affect internal state.
- **No Supabase calls in MemoryStore:** The store is a pure in-memory object. The pipeline runner persists `snapshot()` to Supabase — MemoryStore knows nothing about Supabase.
- **Duplicate guard on lists:** `add_character`, `add_world_rule`, `add_concept`, `add_framework`, `lock_chapter` all guard against duplicate insertion.

### Architecture Decisions Affecting This Task
- `FictionMemory` and `NonFictionMemory` are both created once per job at the start of the pipeline and passed to all engines.
- `snapshot()` is called after each chapter is locked and stored in `chapters.memory_snapshot` (JSONB column).

---

## Handoff from Previous Task

**Files changed by previous task:** `worker/clients/notebooklm_client.py`, `tests/unit/test_notebooklm_client.py`.
**Decisions made:** Graceful fallback pattern (return None, log warning) established for external APIs.
**Context for this task:** All three clients are done. Now build the memory system that engines will share.
**Open questions left:** _(none)_

---

## Implementation Steps

1. Create `worker/memory/store.py` — paste template exactly.
2. Create `tests/unit/test_memory_store.py` — paste template exactly.
3. Run: `pytest tests/unit/test_memory_store.py -v` — verify all 12 tests pass.
4. Run: `ruff check worker/memory/store.py` — verify zero lint errors.
5. Run: `mypy worker/memory/store.py` — verify zero type errors.

---

## Decision Rules

| Scenario | Action |
|----------|--------|
| `get()` called with key not in `_data` | Return `default` argument (defaults to `None`) |
| `add_world_rule()` with already-present rule | Skip silently (no duplicate) |
| `add_concept()` with already-present concept | Skip silently (no duplicate) |
| `lock_chapter()` called twice with same index | Skip second call silently |
| `snapshot()` called | Return deep copy — never the internal dict reference |

---

## Acceptance Criteria

- [ ] WHEN `update()` then `get()` are called THEN value is returned correctly
- [ ] WHEN `snapshot()` is mutated THEN original `_data` is unchanged
- [ ] WHEN `add_world_rule()` is called twice with same rule THEN only one entry exists
- [ ] WHEN `is_concept_used()` is called with a used concept THEN returns `True`
- [ ] WHEN `pytest tests/unit/test_memory_store.py` runs THEN all 12 tests pass

---

## Handoff to Next Task

**Files changed:** _(fill via /task-handoff)_
**Decisions made:** _(fill via /task-handoff)_
**Context for next task:** _(fill via /task-handoff)_
**Open questions:** _(fill via /task-handoff)_
