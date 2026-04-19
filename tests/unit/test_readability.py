"""Unit tests for readability scoring helper."""
import pytest
from unittest.mock import MagicMock, patch
import textstat


def test_textstat_flesch_reading_ease_returns_float():
    score = textstat.flesch_reading_ease("The quick brown fox jumps over the lazy dog.")
    assert isinstance(score, float)
    assert 0 <= score <= 100


def test_textstat_flesch_kincaid_grade_returns_float():
    grade = textstat.flesch_kincaid_grade("The quick brown fox jumps over the lazy dog.")
    assert isinstance(grade, float)


def test_compute_and_store_readability_calls_update():
    try:
        from worker.pipeline.chapter_lock import compute_and_store_readability
    except ImportError:
        pytest.skip("compute_and_store_readability not yet implemented")

    mock_client = MagicMock()
    mock_client.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock()

    compute_and_store_readability(
        client=mock_client,
        job_id="job-1",
        chapter_index=0,
        content="The quick brown fox jumps over the lazy dog. " * 10,
    )

    mock_client.table.assert_called_with("chapters")
    update_call = mock_client.table.return_value.update.call_args[0][0]
    assert "flesch_kincaid_grade" in update_call
    assert "flesch_reading_ease" in update_call
    assert isinstance(update_call["flesch_kincaid_grade"], float)
    assert isinstance(update_call["flesch_reading_ease"], float)


def test_compute_and_store_readability_does_not_raise_on_db_error():
    try:
        from worker.pipeline.chapter_lock import compute_and_store_readability
    except ImportError:
        pytest.skip("compute_and_store_readability not yet implemented")

    mock_client = MagicMock()
    mock_client.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.side_effect = Exception("DB error")

    # Should not raise
    compute_and_store_readability(mock_client, "job-1", 0, "Some content.")
