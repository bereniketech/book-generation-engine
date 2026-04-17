"""Unit test for PipelineRunner with all engines and external clients stubbed."""
from unittest.mock import MagicMock, patch

import pytest

from worker.pipeline.base import JobConfig
from worker.pipeline.runner import PipelineRunner


def make_config(mode: str = "fiction") -> JobConfig:
    return JobConfig(
        job_id="runner-job-1",
        title="Test Book",
        topic="A test topic",
        mode=mode,
        audience="Testers",
        tone="Neutral",
        target_chapters=3,
        llm_provider="anthropic",
        llm_model="claude-sonnet-4-6",
        llm_api_key="k",
        image_provider="dall-e-3",
        image_api_key="k",
    )


def test_runner_completes_fiction_job_with_stubs():
    config = make_config("fiction")
    mock_supabase = MagicMock()
    mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = None
    mock_supabase.table.return_value.upsert.return_value.execute.return_value = None
    mock_supabase.storage.from_.return_value.upload.return_value = None
    mock_supabase.storage.from_.return_value.create_signed_url.return_value = {"signedURL": "https://example.com/bundle.zip"}

    progress_events = []

    # Stub LLMClient, ImageClient, NotebookLMClient at module level
    with patch("worker.pipeline.runner.LLMClient") as MockLLM, \
         patch("worker.pipeline.runner.ImageClient") as MockImage, \
         patch("worker.pipeline.runner.NotebookLMClient") as MockNLM:

        mock_llm_inst = MagicMock()
        # Return valid JSON for all planning engine calls, then chapter content for generation
        import json
        mock_llm_inst.complete.side_effect = [
            json.dumps({"transformation": "t", "outcome": "o", "reader_state_before": "b", "reader_state_after": "a"}),  # Intent
            json.dumps({"demographics": "d", "expectations": "e", "depth_tolerance": "intermediate", "reading_context": "r"}),  # Audience
            json.dumps({"unique_angle": "u", "market_differentiation": "m", "what_book_avoids": "v"}),  # Positioning
            json.dumps({"hook": "h", "unique_premise": "p", "genre": "g"}),  # Concept
            json.dumps({"central_theme": "ct", "moral_tension": "mt", "meaning": "m"}),  # Theme
            json.dumps({"protagonist": {"name": "Hero", "description": "Brave", "arc": "Growth"}, "antagonist": {"name": "Villain", "description": "Evil", "arc": "Fall"}, "supporting": []}),  # Character
            json.dumps({"internal_conflict": "ic", "external_conflict": "ec", "stakes": "s"}),  # Conflict
            json.dumps({"acts": [{"act": 1, "chapters": [{"index": 0, "title": "Ch1", "beats": []}, {"index": 1, "title": "Ch2", "beats": []}, {"index": 2, "title": "Ch3", "beats": []}]}]}),  # Structure
            json.dumps({"endings": [{"type": "happy", "description": "Peace", "score": 8}], "selected": 0}),  # Ending
            "Chapter 1 long content here " * 50,  # Chapter 1 generation
            json.dumps({"passed": True, "issues": [], "severity": "none"}),  # Continuity ch1
            json.dumps({"clarity": 8, "pacing": 8, "redundancy": 8, "coherence": 8, "overall": 8, "passed": True, "feedback": ""}),  # QA ch1
            json.dumps({"tone_consistency": 8, "sentence_variation": 8, "readability": 8, "overall": 8, "passed": True, "feedback": ""}),  # Style ch1
            "Chapter 2 long content here " * 50,  # Chapter 2 generation
            json.dumps({"passed": True, "issues": [], "severity": "none"}),  # Continuity ch2
            json.dumps({"clarity": 8, "pacing": 8, "redundancy": 8, "coherence": 8, "overall": 8, "passed": True, "feedback": ""}),  # QA ch2
            json.dumps({"tone_consistency": 8, "sentence_variation": 8, "readability": 8, "overall": 8, "passed": True, "feedback": ""}),  # Style ch2
            "Chapter 3 long content here " * 50,  # Chapter 3 generation
            json.dumps({"passed": True, "issues": [], "severity": "none"}),  # Continuity ch3
            json.dumps({"clarity": 8, "pacing": 8, "redundancy": 8, "coherence": 8, "overall": 8, "passed": True, "feedback": ""}),  # QA ch3
            json.dumps({"tone_consistency": 8, "sentence_variation": 8, "readability": 8, "overall": 8, "passed": True, "feedback": ""}),  # Style ch3
            json.dumps({"title": "Test Book", "subtitle": "A sub", "description": "Desc", "keywords": ["k1","k2","k3","k4","k5","k6","k7"], "categories": ["Fiction", "Adventure"]}),  # Packaging
            "Cover brief text",  # CoverEngine brief
        ]
        MockLLM.return_value = mock_llm_inst

        mock_image_inst = MagicMock()
        mock_image_inst.generate.return_value = b"fake cover bytes"
        MockImage.return_value = mock_image_inst

        MockNLM.return_value = MagicMock()

        runner = PipelineRunner(config=config, supabase=mock_supabase, progress_callback=lambda e: progress_events.append(e))
        runner.run()

    # Verify job completed
    assert any(e["status"] == "complete" for e in progress_events)
    assert any(e["status"] == "assembling" for e in progress_events)
