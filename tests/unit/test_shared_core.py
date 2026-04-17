"""Unit tests for shared core engines."""
import json
from unittest.mock import MagicMock

import pytest

from worker.memory.store import FictionMemory, NonFictionMemory
from worker.pipeline.base import JobConfig
from worker.pipeline.shared_core import (
    AudienceEngine,
    ContentBlueprintSelectorEngine,
    EntryGateEngine,
    IntentEngine,
    PositioningEngine,
)


def make_config(mode: str = "fiction") -> JobConfig:
    return JobConfig(
        job_id="test-job-1",
        title="The Iron Path",
        topic="Stoicism applied to modern leadership",
        mode=mode,
        audience="Professionals aged 30-50",
        tone="Authoritative yet accessible",
        target_chapters=10,
        llm_provider="anthropic",
        llm_model="claude-sonnet-4-6",
        llm_api_key="test-key",
        image_provider="dall-e-3",
        image_api_key="img-key",
    )


def make_stub_llm(response: str) -> MagicMock:
    llm = MagicMock()
    llm.complete.return_value = response
    return llm


def test_entry_gate_sets_validated_input_and_status():
    config = make_config("fiction")
    mem = FictionMemory(config.job_id)
    engine = EntryGateEngine(llm=make_stub_llm(""), memory=mem, config=config)
    ctx = engine.run({})
    assert ctx["validated_input"]["job_id"] == "test-job-1"
    assert ctx["validated_input"]["mode"] == "fiction"
    assert ctx["status"] == "planning"


def test_intent_engine_parses_json_from_llm():
    config = make_config()
    mem = FictionMemory(config.job_id)
    intent_json = json.dumps({
        "transformation": "From reactive to proactive",
        "outcome": "Confident leadership",
        "reader_state_before": "Stressed",
        "reader_state_after": "Empowered",
    })
    engine = IntentEngine(llm=make_stub_llm(intent_json), memory=mem, config=config)
    ctx = engine.run({})
    assert ctx["intent"]["transformation"] == "From reactive to proactive"
    assert mem.get("intent") == ctx["intent"]


def test_intent_engine_handles_non_json_llm_response():
    config = make_config()
    mem = FictionMemory(config.job_id)
    engine = IntentEngine(llm=make_stub_llm("Not JSON at all"), memory=mem, config=config)
    ctx = engine.run({})
    assert "transformation" in ctx["intent"]


def test_audience_engine_stores_profile_in_memory():
    config = make_config()
    mem = FictionMemory(config.job_id)
    profile_json = json.dumps({
        "demographics": "30-50 professionals",
        "expectations": "Practical advice",
        "depth_tolerance": "intermediate",
        "reading_context": "commute",
    })
    engine = AudienceEngine(llm=make_stub_llm(profile_json), memory=mem, config=config)
    ctx = engine.run({})
    assert mem.get("audience_profile")["depth_tolerance"] == "intermediate"


def test_blueprint_selector_fiction():
    config = make_config("fiction")
    mem = FictionMemory(config.job_id)
    engine = ContentBlueprintSelectorEngine(llm=make_stub_llm(""), memory=mem, config=config)
    ctx = engine.run({})
    assert ctx["branch"] == "fiction"


def test_blueprint_selector_non_fiction():
    config = make_config("non_fiction")
    mem = NonFictionMemory(config.job_id)
    engine = ContentBlueprintSelectorEngine(llm=make_stub_llm(""), memory=mem, config=config)
    ctx = engine.run({})
    assert ctx["branch"] == "non_fiction"
