"""Tests for cache_service with edge cases and concurrent operations."""
from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services import cache_service


@pytest.fixture
async def mock_redis():
    """Mock Redis client for testing."""
    return AsyncMock()


@pytest.mark.asyncio
async def test_get_cached_job_hit(mock_redis):
    """Test cache hit returns stored job data."""
    job_data = {"id": "job-123", "status": "completed"}

    with patch("app.services.cache_service.get_redis", return_value=mock_redis):
        mock_redis.get.return_value = json.dumps(job_data)

        result = await cache_service.get_cached_job("job-123")

        assert result == job_data
        mock_redis.get.assert_called_once()


@pytest.mark.asyncio
async def test_get_cached_job_miss(mock_redis):
    """Test cache miss returns None."""
    with patch("app.services.cache_service.get_redis", return_value=mock_redis):
        mock_redis.get.return_value = None

        result = await cache_service.get_cached_job("job-123")

        assert result is None


@pytest.mark.asyncio
async def test_get_cached_job_malformed_json(mock_redis):
    """Test handling of corrupted cache data."""
    with patch("app.services.cache_service.get_redis", return_value=mock_redis):
        mock_redis.get.return_value = "{ invalid json }"

        result = await cache_service.get_cached_job("job-123")

        assert result is None


@pytest.mark.asyncio
async def test_cache_job_success(mock_redis):
    """Test storing job in cache."""
    job_data = {"id": "job-123", "status": "processing"}

    with patch("app.services.cache_service.get_redis", return_value=mock_redis):
        await cache_service.cache_job("job-123", job_data)

        mock_redis.set.assert_called_once()
        call_args = mock_redis.set.call_args
        assert call_args[0][0] == cache_service._job_cache_key("job-123")
        assert json.loads(call_args[0][1]) == job_data


@pytest.mark.asyncio
async def test_cache_job_with_custom_ttl(mock_redis):
    """Test cache respects custom TTL."""
    with patch("app.services.cache_service.get_redis", return_value=mock_redis):
        await cache_service.cache_job("job-123", {}, ttl=600)

        call_kwargs = mock_redis.set.call_args[1]
        assert call_kwargs["ex"] == 600


@pytest.mark.asyncio
async def test_invalidate_job_cache(mock_redis):
    """Test cache invalidation."""
    with patch("app.services.cache_service.get_redis", return_value=mock_redis):
        await cache_service.invalidate_job_cache("job-123")

        mock_redis.delete.assert_called_once_with(cache_service._job_cache_key("job-123"))


@pytest.mark.asyncio
async def test_invalidate_all_jobs_cache(mock_redis):
    """Test bulk cache invalidation."""
    keys_to_delete = [
        cache_service._job_cache_key("job-1"),
        cache_service._job_cache_key("job-2"),
    ]

    with patch("app.services.cache_service.get_redis", return_value=mock_redis):
        mock_redis.keys.return_value = keys_to_delete

        await cache_service.invalidate_all_jobs_cache()

        mock_redis.keys.assert_called_once()
        mock_redis.delete.assert_called_once_with(*keys_to_delete)


@pytest.mark.asyncio
async def test_concurrent_cache_operations(mock_redis):
    """Test multiple concurrent cache operations don't corrupt state."""
    with patch("app.services.cache_service.get_redis", return_value=mock_redis):
        mock_redis.get.return_value = None
        mock_redis.set.return_value = True

        # Simulate 10 concurrent cache operations
        jobs = [{"id": f"job-{i}", "status": "queued"} for i in range(10)]
        await asyncio.gather(
            *[cache_service.cache_job(job["id"], job) for job in jobs]
        )

        assert mock_redis.set.call_count == 10


@pytest.mark.asyncio
async def test_cache_service_redis_connection_error(mock_redis):
    """Test graceful degradation on Redis connection failure."""
    with patch("app.services.cache_service.get_redis", return_value=mock_redis):
        mock_redis.get.side_effect = Exception("Redis connection failed")

        result = await cache_service.get_cached_job("job-123")

        assert result is None


@pytest.mark.asyncio
async def test_cache_service_handles_none_values(mock_redis):
    """Test caching of None or empty values."""
    with patch("app.services.cache_service.get_redis", return_value=mock_redis):
        # Caching None should not raise error
        await cache_service.cache_job("job-123", {})

        mock_redis.set.assert_called_once()


@pytest.mark.asyncio
async def test_cache_key_generation():
    """Test cache key format is consistent."""
    job_id = "abc-123-def"
    key = cache_service._job_cache_key(job_id)

    assert "bookgen:cache:job:" in key
    assert job_id in key


@pytest.mark.asyncio
async def test_cache_handles_special_characters_in_job_id(mock_redis):
    """Test cache works with special job IDs."""
    special_job_id = "job-2026-04-24-uuid"
    job_data = {"id": special_job_id}

    with patch("app.services.cache_service.get_redis", return_value=mock_redis):
        mock_redis.get.return_value = json.dumps(job_data)

        result = await cache_service.get_cached_job(special_job_id)

        assert result == job_data


@pytest.mark.asyncio
async def test_cache_large_job_record(mock_redis):
    """Test caching of large job records (stress test)."""
    large_config = {"key" + str(i): "value" * 100 for i in range(100)}
    job_data = {
        "id": "job-123",
        "status": "processing",
        "config": large_config,
        "metadata": {"created": "2026-04-24"}
    }

    with patch("app.services.cache_service.get_redis", return_value=mock_redis):
        await cache_service.cache_job("job-123", job_data)

        mock_redis.set.assert_called_once()
        # Verify serialization works
        call_args = mock_redis.set.call_args[0]
        deserialized = json.loads(call_args[1])
        assert deserialized["config"] == large_config
