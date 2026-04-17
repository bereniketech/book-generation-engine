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
