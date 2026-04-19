"""Unit tests for token tracker service."""
import pytest
from unittest.mock import MagicMock, patch

from app.services.token_tracker import record_usage, get_job_usage


@pytest.mark.asyncio
async def test_record_usage_inserts_row():
    mock_client = MagicMock()
    mock_client.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{}])
    with patch("app.services.token_tracker._get_client", return_value=mock_client):
        await record_usage(
            job_id="job-1",
            stage="planning",
            provider="anthropic",
            model="claude-3-haiku-20240307",
            input_tokens=100,
            output_tokens=50,
        )
    mock_client.table.assert_called_with("llm_usage")
    mock_client.table().insert.assert_called_once()
    inserted = mock_client.table().insert.call_args[0][0]
    assert inserted["job_id"] == "job-1"
    assert inserted["input_tokens"] == 100
    assert inserted["output_tokens"] == 50


@pytest.mark.asyncio
async def test_record_usage_does_not_raise_on_db_error():
    mock_client = MagicMock()
    mock_client.table.return_value.insert.return_value.execute.side_effect = Exception("DB error")
    with patch("app.services.token_tracker._get_client", return_value=mock_client):
        # Should not raise
        await record_usage("job-1", "planning", "anthropic", "claude-3-haiku-20240307", 10, 5)


def test_get_job_usage_returns_totals():
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {"stage": "planning", "provider": "anthropic", "model": "claude-3-haiku-20240307", "input_tokens": 100, "output_tokens": 50},
        {"stage": "generation", "provider": "anthropic", "model": "claude-3-haiku-20240307", "input_tokens": 200, "output_tokens": 300},
    ]
    with patch("app.services.token_tracker._get_client", return_value=mock_client):
        result = get_job_usage("job-1")
    assert result["total"]["input_tokens"] == 300
    assert result["total"]["output_tokens"] == 350
    assert len(result["by_stage"]) == 2
