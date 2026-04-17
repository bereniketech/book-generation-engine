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
            "Generate a fiction concept as JSON: "
            '{"hook": "...", "unique_premise": "...", "genre": "..."}'
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
            "Define theme as JSON: "
            '{"central_theme": "...", "moral_tension": "...", "meaning": "..."}'
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
        concept_dump = json.dumps(context.get("concept", {}))
        theme_dump = json.dumps(context.get("theme", {}))
        prompt = (
            f"Concept: {concept_dump}. Theme: {theme_dump}.\n"
            "Define characters as JSON: "
            '{"protagonist": {"name":"...","description":"...","arc":"..."}, '
            '"antagonist": {"name":"...","description":"...","arc":"..."}, "supporting": []}'
        )
        raw = self.llm.complete(prompt, _SYSTEM)
        chars = _safe_json(raw, "protagonist")
        if "protagonist" in chars and isinstance(chars["protagonist"], dict):
            p = chars["protagonist"]
            self.memory.add_character(
                p.get("name", "Protagonist"),
                "protagonist",
                p.get("description", ""),
                p.get("arc", ""),
            )
        if "antagonist" in chars and isinstance(chars["antagonist"], dict):
            a = chars["antagonist"]
            self.memory.add_character(
                a.get("name", "Antagonist"),
                "antagonist",
                a.get("description", ""),
                a.get("arc", ""),
            )
        context["characters"] = chars
        return context


class ConflictEngine(BaseEngine):
    name = "f4_conflict"

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        prompt = (
            f"Characters: {json.dumps(context.get('characters', {}))}.\n"
            "Map conflict as JSON: "
            '{"internal_conflict": "...", "external_conflict": "...", "stakes": "..."}'
        )
        raw = self.llm.complete(prompt, _SYSTEM)
        conflict = _safe_json(raw, "internal_conflict")
        context["conflict"] = conflict
        self.memory.update("conflict", conflict)
        return context


class StructureEngine(BaseEngine):
    name = "f5_structure"

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        conflict_dump = json.dumps(context.get("conflict", {}))
        chapters = self.config.target_chapters
        outline_schema = (
            '{"acts": [{"act": 1, "chapters": '
            '[{"index": 0, "title": "...", "beats": ["..."]}]}]}'
        )
        prompt = (
            f"Conflict: {conflict_dump}. Target chapters: {chapters}.\n"
            f"Create a beat-based outline as JSON: {outline_schema}"
        )
        raw = self.llm.complete(prompt, _SYSTEM)
        structure = _safe_json(raw, "acts")
        context["structure"] = structure
        self.memory.update("structure", structure)
        return context


class EndingEngine(BaseEngine):
    name = "f6_ending"

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        structure_dump = json.dumps(context.get("structure", {}))
        theme_dump = json.dumps(context.get("theme", {}))
        endings_schema = (
            '{"endings": [{"type": "...", "description": "...", "score": 0-10}],'
            ' "selected": 0}'
        )
        prompt = (
            f"Structure: {structure_dump}. Theme: {theme_dump}.\n"
            f"Generate 3 ending options as JSON: {endings_schema}"
        )
        raw = self.llm.complete(prompt, _SYSTEM)
        ending = _safe_json(raw, "endings")
        context["ending"] = ending
        self.memory.update("ending", ending)
        return context


class StoryMemoryInitEngine(BaseEngine):
    name = "f7_story_memory"

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        assert isinstance(self.memory, FictionMemory), (
            "StoryMemoryInitEngine requires FictionMemory"
        )
        # Consolidate all fiction planning into memory
        for key in ("concept", "theme", "conflict", "structure", "ending"):
            if key in context:
                self.memory.update(key, context[key])
        context["fiction_memory_initialised"] = True
        context["memory_snapshot"] = self.memory.snapshot()
        logger.info("[StoryMemory] Initialised for job %s", self.config.job_id)
        return context
