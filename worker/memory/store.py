"""In-memory state tracking for generation engines.

Each engine calls update() to record what it produced.
snapshot() returns the full state as a JSON-serialisable dict for Supabase persistence.
"""
from __future__ import annotations

import copy
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
        return {"job_id": self.job_id, "mode": self.mode, "data": copy.deepcopy(self._data)}


class FictionMemory(MemoryStore):
    """Tracks story-specific state: characters, timeline, world rules, locked chapters."""

    def __init__(self, job_id: str) -> None:
        super().__init__(job_id, "fiction")
        self._data.update({
            "characters": {},
            "timeline": [],
            "world_rules": [],
            "locked_chapters": [],
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
        """Add an established world rule."""
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
            "concepts_introduced": [],
            "frameworks_used": [],
            "evidence_used": [],
            "locked_chapters": [],
            "promise": None,
            "framework": None,
            "content_map": None,
            "research_summary": None,
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
        """Record a piece of evidence as used."""
        self._data["evidence_used"].append({"source": source, "summary": summary})

    def lock_chapter(self, chapter_index: int) -> None:
        """Mark a chapter as locked."""
        if chapter_index not in self._data["locked_chapters"]:
            self._data["locked_chapters"].append(chapter_index)

    def is_concept_used(self, concept: str) -> bool:
        """Return True if this concept was already introduced in a prior chapter."""
        return concept in self._data["concepts_introduced"]
