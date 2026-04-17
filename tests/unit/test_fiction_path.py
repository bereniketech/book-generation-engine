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
