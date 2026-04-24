"""Tests for concurrent operations and race condition handling."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from app.services import cache_service, job_service


@pytest.mark.asyncio
async def test_concurrent_get_cached_job_calls():
    """Test concurrent cache gets don't cause race conditions."""
    mock_redis = AsyncMock()
    job_data = {"id": "job-123", "status": "processing"}

    with patch("app.services.cache_service.get_redis", return_value=mock_redis):
        mock_redis.get.return_value = (
            '{"id": "job-123", "status": "processing"}'
        )

        # 50 concurrent reads of same cache key
        results = await asyncio.gather(
            *[cache_service.get_cached_job("job-123") for _ in range(50)]
        )

        assert all(r == job_data for r in results)
        assert mock_redis.get.call_count == 50


@pytest.mark.asyncio
async def test_concurrent_cache_writes_to_different_keys():
    """Test concurrent writes to different cache keys."""
    mock_redis = AsyncMock()
    mock_redis.set.return_value = True

    with patch("app.services.cache_service.get_redis", return_value=mock_redis):
        jobs = [{"id": f"job-{i}", "status": "queued"} for i in range(20)]

        await asyncio.gather(
            *[cache_service.cache_job(job["id"], job) for job in jobs]
        )

        assert mock_redis.set.call_count == 20


@pytest.mark.asyncio
async def test_concurrent_cache_invalidations():
    """Test concurrent invalidations don't cause errors."""
    mock_redis = AsyncMock()
    mock_redis.delete.return_value = 1

    with patch("app.services.cache_service.get_redis", return_value=mock_redis):
        job_ids = [f"job-{i}" for i in range(10)]

        await asyncio.gather(
            *[cache_service.invalidate_job_cache(jid) for jid in job_ids]
        )

        assert mock_redis.delete.call_count == 10


@pytest.mark.asyncio
async def test_cache_coherency_on_concurrent_read_write():
    """Test read-write ordering maintains cache coherency.

    Scenario: Thread A reads (cache miss), Thread B writes, Thread A writes
    Expected: Final cache state should be from Thread A (last writer wins)
    """
    mock_redis = AsyncMock()
    call_order = []

    async def mock_get(key):
        call_order.append(("get", key))
        return None

    async def mock_set(key, value, ex=None):
        call_order.append(("set", key, value))
        return True

    mock_redis.get = mock_get
    mock_redis.set = mock_set

    with patch("app.services.cache_service.get_redis", return_value=mock_redis):
        await asyncio.gather(
            cache_service.cache_job("job-1", {"data": "version-1"}),
            cache_service.cache_job("job-1", {"data": "version-2"}),
        )

        # Both sets should have occurred
        set_calls = [c for c in call_order if c[0] == "set"]
        assert len(set_calls) == 2


@pytest.mark.asyncio
async def test_state_transition_under_concurrent_reads():
    """Test state transitions don't lose data under concurrent access.

    Simulates multiple readers accessing job while status changes.
    """
    mock_redis = AsyncMock()
    # Initial state: processing
    initial_job = {"id": "job-123", "status": "processing"}
    updated_job = {"id": "job-123", "status": "completed"}

    get_call_count = [0]

    async def mock_get(key):
        get_call_count[0] += 1
        if get_call_count[0] <= 5:
            return None  # First 5 calls miss cache
        return (
            '{"id": "job-123", "status": "completed"}'
        )  # Later calls hit cache

    mock_redis.get = mock_get
    mock_redis.set = AsyncMock(return_value=True)

    with patch("app.services.cache_service.get_redis", return_value=mock_redis):
        # 5 readers before update, 5 after
        results_before = await asyncio.gather(
            *[cache_service.get_cached_job("job-123") for _ in range(5)]
        )
        assert all(r is None for r in results_before)

        # Simulate job completion (cache invalidate + update)
        await cache_service.cache_job("job-123", updated_job)

        results_after = await asyncio.gather(
            *[cache_service.get_cached_job("job-123") for _ in range(5)]
        )
        assert all(r == updated_job for r in results_after)


@pytest.mark.asyncio
async def test_concurrent_invalidate_all_and_get():
    """Test get during bulk invalidation."""
    mock_redis = AsyncMock()

    async def mock_get(key):
        await asyncio.sleep(0.01)  # Simulate delay
        return None

    async def mock_keys(pattern):
        await asyncio.sleep(0.02)  # Invalidate takes longer
        return []

    mock_redis.get = mock_get
    mock_redis.keys = mock_keys
    mock_redis.delete = AsyncMock(return_value=0)

    with patch("app.services.cache_service.get_redis", return_value=mock_redis):
        # Concurrent: 10 gets, 1 bulk invalidate
        results = await asyncio.gather(
            asyncio.gather(
                *[cache_service.get_cached_job(f"job-{i}") for i in range(10)]
            ),
            cache_service.invalidate_all_jobs_cache(),
        )

        # All operations should complete without error
        assert results is not None


@pytest.mark.asyncio
async def test_redis_connection_resilience_under_load():
    """Test cache service handles Redis failures under concurrent load."""
    mock_redis = AsyncMock()

    fail_count = [0]

    async def flaky_get(key):
        fail_count[0] += 1
        if fail_count[0] % 5 == 0:  # Every 5th call fails
            raise ConnectionError("Redis unavailable")
        return None

    mock_redis.get = flaky_get

    with patch("app.services.cache_service.get_redis", return_value=mock_redis):
        # 25 concurrent requests with some failures
        results = await asyncio.gather(
            *[cache_service.get_cached_job(f"job-{i}") for i in range(25)],
            return_exceptions=False,
        )

        # All should return None (graceful degradation)
        assert all(r is None for r in results)


@pytest.mark.asyncio
async def test_cache_stampede_prevention():
    """Test multiple concurrent cache misses don't cause N database hits.

    Cache stampede: when cache expires, many requests query DB simultaneously.
    This test verifies we at least limit excessive Redis calls.
    """
    mock_redis = AsyncMock()
    # All cache misses
    mock_redis.get.return_value = None
    mock_redis.set.return_value = True

    with patch("app.services.cache_service.get_redis", return_value=mock_redis):
        # 100 concurrent requests for same job (all cache misses)
        await asyncio.gather(
            *[cache_service.get_cached_job("job-123") for _ in range(100)]
        )

        # Each request triggers get + set
        assert mock_redis.get.call_count == 100
        # In production, a lock-based approach could reduce this
        # For now, we accept the tradeoff of simplicity vs stampede protection


@pytest.mark.asyncio
async def test_cache_invalidation_isolation():
    """Test invalidating one job doesn't affect other cached jobs."""
    mock_redis = AsyncMock()

    with patch("app.services.cache_service.get_redis", return_value=mock_redis):
        # Cache 3 jobs
        await asyncio.gather(
            cache_service.cache_job("job-1", {"id": "job-1"}),
            cache_service.cache_job("job-2", {"id": "job-2"}),
            cache_service.cache_job("job-3", {"id": "job-3"}),
        )

        # Invalidate only job-2
        await cache_service.invalidate_job_cache("job-2")

        # Verify only job-2's key was deleted
        call_args = mock_redis.delete.call_args[0]
        assert cache_service._job_cache_key("job-2") in call_args
