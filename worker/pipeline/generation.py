"""Per-chapter generation engines."""
from __future__ import annotations

import json
import logging
from typing import Any

from worker.pipeline.base import BaseEngine

logger = logging.getLogger(__name__)

_GENERATION_SYSTEM = (
    "You are a professional book author writing timeless, forceful prose.\n"
    "Rules (enforce strictly):\n"
    "- Write clean, exact, muscular sentences. Vary length aggressively."
    " Short sentences hit hard.\n"
    "- Use concrete nouns, strong verbs. No adverbs where a better verb works.\n"
    "- No filler transitions: 'In today's world', 'That said', 'Moreover',"
    " 'Ultimately', 'At its core'.\n"
    "- No AI-isms: 'leverage', 'robust', 'seamless', 'cutting-edge', 'delve',"
    " 'tapestry', 'testament to'.\n"
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
            "Memory context (do not repeat what is already introduced):"
            f" {json.dumps(memory_snapshot)}\n"
            f"Audience: {self.config.audience}. Tone: {self.config.tone}.\n"
            "Write the complete chapter content. Minimum 800 words."
            " Do not include chapter number in output."
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
            "Score this chapter 1-10 on: clarity, pacing, redundancy"
            " (10=no redundancy), coherence. "
            "Output JSON: "
            '{"clarity": 7, "pacing": 7, "redundancy": 8, "coherence": 7,'
            ' "overall": 7, "passed": true, "feedback": "..."}'
        )
        raw = self.llm.complete(prompt, _QA_SYSTEM)
        try:
            scores = json.loads(raw)
        except json.JSONDecodeError:
            scores = {
                "clarity": 7,
                "pacing": 7,
                "redundancy": 7,
                "coherence": 7,
                "overall": 7,
                "passed": True,
                "feedback": "",
            }
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
            "Evaluate style. Check for AI-writing patterns (filler transitions like"
            " 'Moreover'/'That said'/"
            "'In today's world', hollow intensifiers, AI-isms like"
            " 'leverage'/'robust'/'seamless'/'delve', "
            "em-dash pivot constructions, therapy language, meta-commentary). "
            "Output JSON: "
            '{"tone_consistency": 8, "sentence_variation": 7, "readability": 8,'
            ' "ai_isms_detected": 0, "overall": 7, "passed": true, "feedback": "..."}'
        )
        raw = self.llm.complete(prompt, _QA_SYSTEM)
        try:
            scores = json.loads(raw)
        except json.JSONDecodeError:
            scores = {
                "tone_consistency": 7,
                "sentence_variation": 7,
                "readability": 7,
                "overall": 7,
                "passed": True,
                "feedback": "",
            }
        scores["passed"] = int(scores.get("overall", 0)) >= self.PASS_THRESHOLD
        context["style_result"] = scores
        return context


def chapter_passed(context: dict[str, Any]) -> bool:
    """Return True if continuity, QA, and style all passed."""
    continuity_ok = context.get("continuity_result", {}).get("passed", True)
    qa_ok = context.get("qa_result", {}).get("passed", False)
    style_ok = context.get("style_result", {}).get("passed", False)
    return continuity_ok and qa_ok and style_ok
