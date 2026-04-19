"""Unit tests for Redis progress service using a mock Redis client."""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.progress import publish_progress, get_snapshot, _channel, _snapshot_key


@pytest.mark.asyncio
async def test_publish_progress_publishes_to_correct_channel():
    mock_redis = AsyncMock()
    with patch("app.services.progress.get_redis", return_value=mock_redis):
        event = {"event": "chapter_locked", "job_id": "job-1", "chapter_index": 0, "total_chapters": 10, "stage": "generating"}
        await publish_progress("job-1", event)
        mock_redis.publish.assert_awaited_once_with("bookgen:progress:job-1", json.dumps(event))
        mock_redis.set.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_snapshot_returns_none_when_missing():
    mock_redis = AsyncMock()
    mock_redis.get.return_value = None
    with patch("app.services.progress.get_redis", return_value=mock_redis):
        result = await get_snapshot("job-99")
        assert result is None


@pytest.mark.asyncio
async def test_get_snapshot_returns_parsed_json():
    stored = json.dumps({"event": "chapter_locked", "job_id": "job-1", "chapter_index": 2, "total_chapters": 10, "stage": "generating"})
    mock_redis = AsyncMock()
    mock_redis.get.return_value = stored
    with patch("app.services.progress.get_redis", return_value=mock_redis):
        result = await get_snapshot("job-1")
        assert result["event"] == "chapter_locked"
        assert result["chapter_index"] == 2


def test_channel_key_format():
    assert _channel("abc-123") == "bookgen:progress:abc-123"


def test_snapshot_key_format():
    assert _snapshot_key("abc-123") == "bookgen:snapshot:abc-123"
