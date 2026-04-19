"""Unit tests for job recovery scan."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone, timedelta

from worker.recovery import scan_and_recover


@pytest.mark.asyncio
async def test_scan_and_recover_no_stale_jobs():
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.lt.return_value.execute.return_value.data = []
    mock_channel = AsyncMock()

    with patch("worker.recovery.create_client", return_value=mock_client):
        count = await scan_and_recover(mock_channel)

    assert count == 0


@pytest.mark.asyncio
async def test_scan_and_recover_one_stale_job_no_locked_chapters():
    mock_client = MagicMock()
    stale_job = {"id": "job-1", "config": {"title": "Test"}, "updated_at": "2024-01-01T00:00:00Z"}

    mock_client.table.return_value.select.return_value.eq.return_value.lt.return_value.execute.return_value.data = [stale_job]
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = []
    mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

    mock_channel = AsyncMock()
    mock_exchange = AsyncMock()
    mock_channel.get_exchange.return_value = mock_exchange

    with patch("worker.recovery.create_client", return_value=mock_client):
        count = await scan_and_recover(mock_channel)

    assert count == 1
    update_call = mock_client.table.return_value.update.call_args[0][0]
    assert update_call["chapter_cursor"] == 0
    assert update_call["status"] == "queued"


@pytest.mark.asyncio
async def test_scan_and_recover_cursor_set_to_next_after_last_locked():
    mock_client = MagicMock()
    stale_job = {"id": "job-2", "config": {}, "updated_at": "2024-01-01T00:00:00Z"}
    mock_client.table.return_value.select.return_value.eq.return_value.lt.return_value.execute.return_value.data = [stale_job]
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [{"index": 4}]
    mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

    mock_channel = AsyncMock()
    mock_exchange = AsyncMock()
    mock_channel.get_exchange.return_value = mock_exchange

    with patch("worker.recovery.create_client", return_value=mock_client):
        count = await scan_and_recover(mock_channel)

    assert count == 1
    update_call = mock_client.table.return_value.update.call_args[0][0]
    assert update_call["chapter_cursor"] == 5  # next after last locked
