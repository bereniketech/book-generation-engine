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

_RESEARCH_SYSTEM = "You are a research analyst. Be specific, cite examples, no filler."


def _safe_json(raw: str, fallback_key: str) -> dict[str, Any]:
    try:
        return json.loads(raw)  # type: ignore[no-any-return]
    except json.JSONDecodeError:
        return {fallback_key: raw}


class ResearchStep:
    """Not a BaseEngine — runs before engines. Calls NotebookLM and stores research summary."""

    def __init__(
        self,
        notebooklm_client: NotebookLMClient,
        llm: Any,
        config: Any,
        memory: NonFictionMemory,
    ) -> None:
        self.notebooklm = notebooklm_client
        self.llm = llm
        self.config = config
        self.memory = memory

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        logger.info("[Research] Starting NotebookLM research for job %s", self.config.job_id)
        summary = self.notebooklm.research(self.config.topic, max_wait_seconds=300)
        if summary is None:
            logger.warning(
                "[Research] NotebookLM unavailable — falling back to LLM synthesis for job %s",
                self.config.job_id,
            )
            synthesis_prompt = (
                f"Provide a comprehensive research synthesis on: {self.config.topic}\n"
                "Cover key concepts, evidence/case studies, expert perspectives, "
                "current trends, and practical applications."
            )
            summary = self.llm.complete(synthesis_prompt, _RESEARCH_SYSTEM)
        self.memory.update("research_summary", summary)
        context["research_summary"] = summary
        return context


class PromiseEngine(BaseEngine):
    name = "n1_promise"

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        research = context.get("research_summary", "")
        promise_schema = (
            '{"transformation": "...", "specific_outcome": "...", "time_frame": "..."}'
        )
        prompt = (
            f"Book: '{self.config.title}'. Research: {research[:2000]}."
            f" Audience: '{self.config.audience}'.\n"
            f"Define the reader promise as JSON: {promise_schema}"
        )
        raw = self.llm.complete(prompt, _SYSTEM)
        promise = _safe_json(raw, "transformation")
        context["promise"] = promise
        self.memory.update("promise", promise)
        return context


class FrameworkEngine(BaseEngine):
    name = "n2_framework"

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        framework_schema = (
            '{"framework_name": "...", "steps": [{"step": 1, "name": "...", "description": "..."}]}'
        )
        research_snippet = str(context.get("research_summary", ""))[:1000]
        prompt = (
            f"Promise: {json.dumps(context.get('promise', {}))}."
            f" Research: {research_snippet}.\n"
            f"Define the step-by-step framework as JSON: {framework_schema}"
        )
        raw = self.llm.complete(prompt, _SYSTEM)
        framework = _safe_json(raw, "framework_name")
        context["framework"] = framework
        self.memory.update("framework", framework)
        return context


class ContentMapEngine(BaseEngine):
    name = "n3_content_map"

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        chapter_schema = (
            '{"chapters": [{"index": 0, "title": "...",'
            ' "key_points": ["..."], "framework_step": 1}]}'
        )
        prompt = (
            f"Framework: {json.dumps(context.get('framework', {}))}."
            f" Target chapters: {self.config.target_chapters}.\n"
            f"Create chapter breakdown as JSON: {chapter_schema}"
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
        evidence_schema = (
            '{"evidence": [{"source": "...", "summary": "...", "chapter_index": 0}]}'
        )
        prompt = (
            f"Research summary: {research[:2000]}."
            f" Framework: {json.dumps(context.get('framework', {}))}.\n"
            f"Extract 5-10 pieces of evidence as JSON: {evidence_schema}"
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
        assert isinstance(self.memory, NonFictionMemory), (
            "KnowledgeMemoryInitEngine requires NonFictionMemory"
        )
        for key in ("promise", "framework", "content_map", "evidence", "research_summary"):
            if key in context:
                self.memory.update(key, context[key])
        context["non_fiction_memory_initialised"] = True
        context["memory_snapshot"] = self.memory.snapshot()
        logger.info("[KnowledgeMemory] Initialised for job %s", self.config.job_id)
        return context
