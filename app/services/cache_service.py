"""Redis-backed caching service for frequently accessed data.

Provides efficient caching of job records and other hot-path data to reduce
database load and improve response times for repeated queries.
"""
from __future__ import annotations

import json
import os
from typing import Any

import redis.asyncio as aioredis

from app.core.logging import get_logger

log = get_logger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
CACHE_TTL = 300  # 5 minutes for job records
_redis_client: aioredis.Redis | None = None


def _job_cache_key(job_id: str) -> str:
    """Generate cache key for job record."""
    return f"bookgen:cache:job:{job_id}"


async def get_redis() -> aioredis.Redis:
    """Get shared Redis client instance."""
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(REDIS_URL, decode_responses=True)
    return _redis_client


async def get_cached_job(job_id: str) -> dict | None:
    """Retrieve cached job record, or None if not in cache.

    Args:
        job_id: Job UUID

    Returns:
        Job dict if found in cache, None otherwise
    """
    try:
        r = await get_redis()
        cached = await r.get(_job_cache_key(job_id))
        if cached:
            log.debug("cache.job.hit", job_id=job_id)
            return json.loads(cached)
        log.debug("cache.job.miss", job_id=job_id)
        return None
    except Exception as e:
        log.warning("cache.get_error", job_id=job_id, error=str(e))
        return None


async def cache_job(job_id: str, job_data: dict, ttl: int = CACHE_TTL) -> None:
    """Cache a job record for fast retrieval.

    Args:
        job_id: Job UUID
        job_data: Job record dict to cache
        ttl: Time to live in seconds (default: 5 minutes)
    """
    try:
        r = await get_redis()
        await r.set(_job_cache_key(job_id), json.dumps(job_data), ex=ttl)
        log.debug("cache.job.stored", job_id=job_id, ttl=ttl)
    except Exception as e:
        log.warning("cache.set_error", job_id=job_id, error=str(e))


async def invalidate_job_cache(job_id: str) -> None:
    """Invalidate cached job record (e.g., after update).

    Args:
        job_id: Job UUID to invalidate
    """
    try:
        r = await get_redis()
        await r.delete(_job_cache_key(job_id))
        log.debug("cache.job.invalidated", job_id=job_id)
    except Exception as e:
        log.warning("cache.delete_error", job_id=job_id, error=str(e))


async def invalidate_all_jobs_cache() -> None:
    """Invalidate all cached job records.

    Used when bulk operations affect multiple jobs or during cache purges.
    """
    try:
        r = await get_redis()
        pattern = _job_cache_key("*")
        keys = await r.keys(pattern)
        if keys:
            await r.delete(*keys)
            log.debug("cache.jobs.all_invalidated", count=len(keys))
    except Exception as e:
        log.warning("cache.bulk_delete_error", error=str(e))
