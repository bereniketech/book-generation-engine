"""Unit tests for non-fiction path engines."""
import json
from unittest.mock import MagicMock

import pytest

from worker.clients.notebooklm_client import NotebookLMClient
from worker.memory.store import NonFictionMemory
from worker.pipeline.base import JobConfig
from worker.pipeline.non_fiction_path import (
    ContentMapEngine,
    EvidenceEngine,
    FrameworkEngine,
    KnowledgeMemoryInitEngine,
    PromiseEngine,
    ResearchStep,
)


def make_config() -> JobConfig:
    return JobConfig(
        job_id="nf-job-1",
        title="The Stoic Leader",
        topic="Stoicism applied to modern leadership",
        mode="non_fiction",
        audience="Executives",
        tone="Authoritative",
        target_chapters=10,
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


def test_research_step_uses_notebooklm_summary():
    config = make_config()
    mem = NonFictionMemory(config.job_id)
    mock_nlm = MagicMock(spec=NotebookLMClient)
    mock_nlm.research.return_value = "Rich research summary from NotebookLM."
    step = ResearchStep(notebooklm_client=mock_nlm, llm=stub_llm(""), config=config, memory=mem)
    ctx = step.run({})
    assert ctx["research_summary"] == "Rich research summary from NotebookLM."
    assert mem.get("research_summary") == "Rich research summary from NotebookLM."


def test_research_step_falls_back_to_llm_when_notebooklm_returns_none():
    config = make_config()
    mem = NonFictionMemory(config.job_id)
    mock_nlm = MagicMock(spec=NotebookLMClient)
    mock_nlm.research.return_value = None
    llm = stub_llm("LLM synthesised research.")
    step = ResearchStep(notebooklm_client=mock_nlm, llm=llm, config=config, memory=mem)
    ctx = step.run({})
    assert ctx["research_summary"] == "LLM synthesised research."
    llm.complete.assert_called_once()


def test_promise_engine_stores_promise():
    config = make_config()
    mem = NonFictionMemory(config.job_id)
    promise_json = json.dumps({"transformation": "Calm leader", "specific_outcome": "Better decisions", "time_frame": "90 days"})
    engine = PromiseEngine(llm=stub_llm(promise_json), memory=mem, config=config)
    ctx = engine.run({"research_summary": "summary"})
    assert ctx["promise"]["transformation"] == "Calm leader"
    assert mem.get("promise")["transformation"] == "Calm leader"


def test_evidence_engine_adds_evidence_to_memory():
    config = make_config()
    mem = NonFictionMemory(config.job_id)
    evidence_json = json.dumps({"evidence": [
        {"source": "Harvard 2021", "summary": "Leaders who meditate are 30% more effective", "chapter_index": 2}
    ]})
    engine = EvidenceEngine(llm=stub_llm(evidence_json), memory=mem, config=config)
    engine.run({"research_summary": "", "framework": {}})
    assert len(mem.get("evidence_used")) == 1
    assert mem.get("evidence_used")[0]["source"] == "Harvard 2021"


def test_knowledge_memory_init_sets_flag():
    config = make_config()
    mem = NonFictionMemory(config.job_id)
    engine = KnowledgeMemoryInitEngine(llm=stub_llm(""), memory=mem, config=config)
    ctx = engine.run({"promise": {}, "framework": {}, "content_map": {}, "evidence": {}, "research_summary": "x"})
    assert ctx["non_fiction_memory_initialised"] is True
    assert "memory_snapshot" in ctx
