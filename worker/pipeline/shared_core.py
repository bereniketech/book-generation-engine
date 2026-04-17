"""Shared core pipeline engines. Run for both fiction and non-fiction."""
from __future__ import annotations

import json
import logging
from typing import Any

from worker.pipeline.base import BaseEngine

logger = logging.getLogger(__name__)


class EntryGateEngine(BaseEngine):
    name = "entry_gate"

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        """Validate job config and produce validated_input dict."""
        logger.info("[EntryGate] Validating job %s", self.config.job_id)
        validated = {
            "job_id": self.config.job_id,
            "title": self.config.title.strip(),
            "topic": self.config.topic.strip(),
            "mode": self.config.mode,
            "audience": self.config.audience.strip(),
            "tone": self.config.tone.strip(),
            "target_chapters": self.config.target_chapters,
        }
        context["validated_input"] = validated
        context["status"] = "planning"
        logger.info("[EntryGate] Validated input for job %s", self.config.job_id)
        return context


class IntentEngine(BaseEngine):
    name = "intent_engine"

    SYSTEM = "You are a book strategy expert. Output JSON only."
    PROMPT_TEMPLATE = (
        "Book: '{title}'. Topic: '{topic}'. Mode: {mode}. Audience: {audience}.\n"
        "Define the book's intent as JSON: "
        '{{"transformation": "...", "outcome": "...", '
        '"reader_state_before": "...", "reader_state_after": "..."}}'
    )

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        logger.info("[IntentEngine] Running for job %s", self.config.job_id)
        prompt = self.PROMPT_TEMPLATE.format(
            title=self.config.title,
            topic=self.config.topic,
            mode=self.config.mode,
            audience=self.config.audience,
        )
        raw = self.llm.complete(prompt, self.SYSTEM)
        try:
            intent = json.loads(raw)
        except json.JSONDecodeError:
            intent = {
                "transformation": raw,
                "outcome": "",
                "reader_state_before": "",
                "reader_state_after": "",
            }
        context["intent"] = intent
        self.memory.update("intent", intent)
        return context


class AudienceEngine(BaseEngine):
    name = "audience_engine"

    SYSTEM = "You are an audience analyst. Output JSON only."
    PROMPT_TEMPLATE = (
        "Book: '{title}'. Audience: '{audience}'. Tone: '{tone}'.\n"
        "Define the audience profile as JSON: "
        '{{"demographics": "...", "expectations": "...", '
        '"depth_tolerance": "beginner|intermediate|advanced", "reading_context": "..."}}'
    )

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        logger.info("[AudienceEngine] Running for job %s", self.config.job_id)
        prompt = self.PROMPT_TEMPLATE.format(
            title=self.config.title,
            audience=self.config.audience,
            tone=self.config.tone,
        )
        raw = self.llm.complete(prompt, self.SYSTEM)
        try:
            audience_profile = json.loads(raw)
        except json.JSONDecodeError:
            audience_profile = {
                "demographics": raw,
                "expectations": "",
                "depth_tolerance": "intermediate",
                "reading_context": "",
            }
        context["audience_profile"] = audience_profile
        self.memory.update("audience_profile", audience_profile)
        return context


class PositioningEngine(BaseEngine):
    name = "positioning_engine"

    SYSTEM = "You are a book positioning strategist. Output JSON only."
    PROMPT_TEMPLATE = (
        "Book: '{title}'. Topic: '{topic}'. Audience: '{audience}'.\n"
        "Define positioning as JSON: "
        '{{ "unique_angle": "...", "market_differentiation": "...", "what_book_avoids": "..." }}'
    )

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        logger.info("[PositioningEngine] Running for job %s", self.config.job_id)
        prompt = self.PROMPT_TEMPLATE.format(
            title=self.config.title,
            topic=self.config.topic,
            audience=self.config.audience,
        )
        raw = self.llm.complete(prompt, self.SYSTEM)
        try:
            positioning = json.loads(raw)
        except json.JSONDecodeError:
            positioning = {
                "unique_angle": raw,
                "market_differentiation": "",
                "what_book_avoids": "",
            }
        context["positioning"] = positioning
        self.memory.update("positioning", positioning)
        return context


class ContentBlueprintSelectorEngine(BaseEngine):
    name = "content_blueprint_selector"

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        logger.info("[BlueprintSelector] Mode=%s for job %s", self.config.mode, self.config.job_id)
        context["branch"] = self.config.mode  # "fiction" or "non_fiction"
        return context
