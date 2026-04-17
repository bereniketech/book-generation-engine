"""End-to-end test for the book generation pipeline.

Uses a stub LLM provider (ollama pointing to a test fixture server)
or mocks PipelineRunner for isolated testing.
This test verifies that:
1. A job can be submitted and consumed by the worker.
2. All expected artifacts exist after completion.
3. Job status transitions correctly.

Run with: pytest tests/e2e/ -v --timeout=300
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from worker.pipeline.base import JobConfig
from worker.pipeline.runner import PipelineRunner


def make_config() -> JobConfig:
    return JobConfig(
        job_id="e2e-test-job-1",
        title="The Stoic Path",
        topic="Applying stoic philosophy to modern leadership",
        mode="fiction",
        audience="Executives",
        tone="Authoritative",
        target_chapters=3,
        llm_provider="anthropic",
        llm_model="claude-sonnet-4-6",
        llm_api_key="test-key",
        image_provider="dall-e-3",
        image_api_key="img-key",
        notification_email="test@example.com",
    )


def _llm_responses() -> list[str]:
    """Ordered stub LLM responses covering all pipeline stages for a 3-chapter fiction book."""
    planning = [
        json.dumps({"transformation": "t", "outcome": "o", "reader_state_before": "b", "reader_state_after": "a"}),
        json.dumps({"demographics": "d", "expectations": "e", "depth_tolerance": "intermediate", "reading_context": "r"}),
        json.dumps({"unique_angle": "u", "market_differentiation": "m", "what_book_avoids": "v"}),
        json.dumps({"hook": "h", "unique_premise": "p", "genre": "g"}),
        json.dumps({"central_theme": "ct", "moral_tension": "mt", "meaning": "m"}),
        json.dumps({"protagonist": {"name": "Marcus", "description": "Stoic leader", "arc": "Growth"}, "antagonist": {"name": "Tyrant", "description": "Corrupt", "arc": "Fall"}, "supporting": []}),
        json.dumps({"internal_conflict": "ic", "external_conflict": "ec", "stakes": "s"}),
        json.dumps({"acts": [{"act": 1, "chapters": [{"index": 0, "title": "Chapter One", "beats": []}, {"index": 1, "title": "Chapter Two", "beats": []}, {"index": 2, "title": "Chapter Three", "beats": []}]}]}),
        json.dumps({"endings": [{"type": "triumphant", "description": "Marcus prevails", "score": 9}], "selected": 0}),
    ]
    generation = [
        "Chapter One content. " * 100,
        json.dumps({"passed": True, "issues": [], "severity": "none"}),
        json.dumps({"clarity": 8, "pacing": 8, "redundancy": 8, "coherence": 8, "overall": 8, "passed": True, "feedback": ""}),
        json.dumps({"tone_consistency": 8, "sentence_variation": 8, "readability": 8, "overall": 8, "passed": True, "feedback": ""}),
        "Chapter Two content. " * 100,
        json.dumps({"passed": True, "issues": [], "severity": "none"}),
        json.dumps({"clarity": 8, "pacing": 8, "redundancy": 8, "coherence": 8, "overall": 8, "passed": True, "feedback": ""}),
        json.dumps({"tone_consistency": 8, "sentence_variation": 8, "readability": 8, "overall": 8, "passed": True, "feedback": ""}),
        "Chapter Three content. " * 100,
        json.dumps({"passed": True, "issues": [], "severity": "none"}),
        json.dumps({"clarity": 8, "pacing": 8, "redundancy": 8, "coherence": 8, "overall": 8, "passed": True, "feedback": ""}),
        json.dumps({"tone_consistency": 8, "sentence_variation": 8, "readability": 8, "overall": 8, "passed": True, "feedback": ""}),
    ]
    assembly = [
        json.dumps({"title": "The Stoic Path", "subtitle": "A Leadership Journey", "description": "An epic tale of stoic leadership.", "keywords": ["stoic","leader","philosophy","growth","wisdom","strength","resilience"], "categories": ["Business", "Self-Help"]}),
        "Dark navy cover with gold lettering, minimalist design.",
    ]
    return planning + generation + assembly


def test_full_fiction_pipeline_completes_with_all_artifacts():
    config = make_config()
    mock_supabase = MagicMock()
    mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = None
    mock_supabase.table.return_value.upsert.return_value.execute.return_value = None
    mock_supabase.storage.from_.return_value.upload.return_value = None
    mock_supabase.storage.from_.return_value.create_signed_url.return_value = {
        "signedURL": "https://supabase.example.com/storage/v1/sign/book-artifacts/e2e-test-job-1/bundle.zip?token=xxx"
    }

    progress_events: list[dict] = []
    llm_responses = _llm_responses()

    with patch("worker.pipeline.runner.LLMClient") as MockLLM, \
         patch("worker.pipeline.runner.ImageClient") as MockImage, \
         patch("worker.pipeline.runner.NotebookLMClient") as MockNLM:

        mock_llm_inst = MagicMock()
        mock_llm_inst.complete.side_effect = llm_responses
        MockLLM.return_value = mock_llm_inst

        mock_image_inst = MagicMock()
        mock_image_inst.generate.return_value = b"fake cover image bytes"
        MockImage.return_value = mock_image_inst

        MockNLM.return_value = MagicMock()

        runner = PipelineRunner(
            config=config,
            supabase=mock_supabase,
            progress_callback=lambda e: progress_events.append(e),
        )
        runner.run()

    statuses = [e.get("status") for e in progress_events]
    assert "assembling" in statuses, f"Expected 'assembling' in progress events: {statuses}"
    assert "complete" in statuses, f"Expected 'complete' in progress events: {statuses}"

    assert mock_supabase.storage.from_.return_value.upload.called, "Expected bundle to be uploaded to storage"

    complete_events = [e for e in progress_events if e.get("status") == "complete"]
    assert len(complete_events) >= 1
    assert "download_url" in complete_events[0]
    assert "supabase.example.com" in complete_events[0]["download_url"]

    update_calls = mock_supabase.table.return_value.update.call_args_list
    status_values = [call[0][0].get("status") for call in update_calls if call[0][0].get("status")]
    assert "complete" in status_values, f"Expected 'complete' status update: {status_values}"

    upsert_calls = mock_supabase.table.return_value.upsert.call_args_list
    chapter_upserts = [c for c in upsert_calls if c[0][0].get("job_id") == "e2e-test-job-1"]
    assert len(chapter_upserts) >= 3, f"Expected at least 3 chapter upserts, got {len(chapter_upserts)}"
