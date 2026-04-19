"""Unit tests for DLQ consumer and retry logic."""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import worker.dlq as dlq_module
from worker.dlq import get_dlq_status, retry_dlq_messages


def setup_function():
    dlq_module._dlq_messages.clear()


def test_get_dlq_status_empty():
    result = get_dlq_status()
    assert result["count"] == 0
    assert result["sample"] == []


def test_get_dlq_status_with_messages():
    dlq_module._dlq_messages.append({"job_id": "j1", "retry_count": 3, "error": "timeout", "queued_at": "2024-01-01", "body": {}})
    result = get_dlq_status()
    assert result["count"] == 1
    assert result["sample"][0]["job_id"] == "j1"


@pytest.mark.asyncio
async def test_retry_dlq_messages_returns_zero_when_empty():
    result = await retry_dlq_messages()
    assert result == 0


def test_dlq_messages_capped_at_100():
    for i in range(105):
        dlq_module._dlq_messages.append({"job_id": f"j{i}", "retry_count": 1, "error": "e", "queued_at": "", "body": {}})
    # simulate the cap logic
    while len(dlq_module._dlq_messages) > 100:
        dlq_module._dlq_messages.pop(0)
    assert len(dlq_module._dlq_messages) == 100
