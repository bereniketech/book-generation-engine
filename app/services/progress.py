"""Redis pub/sub progress store for multi-worker job progress broadcasting."""
from __future__ import annotations

import json
import os
from typing import AsyncGenerator

import redis.asyncio as aioredis

from app.core.logging import get_logger

log = get_logger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
_redis_client: aioredis.Redis | None = None


def _channel(job_id: str) -> str:
    return f"bookgen:progress:{job_id}"


def _snapshot_key(job_id: str) -> str:
    return f"bookgen:snapshot:{job_id}"


async def get_redis() -> aioredis.Redis:
    """Return a shared Redis client, creating it on first call."""
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(REDIS_URL, decode_responses=True)
    return _redis_client


async def publish_progress(job_id: str, event: dict) -> None:
    """Publish a progress event to the job's Redis channel.
    Also stores event as the latest snapshot.
    """
    r = await get_redis()
    payload = json.dumps(event)
    await r.publish(_channel(job_id), payload)
    await r.set(_snapshot_key(job_id), payload, ex=3600)  # snapshot expires in 1 hour
    log.debug(
        "progress.published",
        job_id=job_id,
        event_type=event.get("event"),
    )


async def get_snapshot(job_id: str) -> dict | None:
    """Return the latest progress snapshot for a job, or None if not found."""
    r = await get_redis()
    raw = await r.get(_snapshot_key(job_id))
    if raw is None:
        return None
    return json.loads(raw)


async def subscribe_progress(job_id: str) -> AsyncGenerator[dict, None]:
    """Async generator that yields progress events from Redis pub/sub for a job."""
    r = aioredis.from_url(REDIS_URL, decode_responses=True)
    pubsub = r.pubsub()
    await pubsub.subscribe(_channel(job_id))
    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                yield json.loads(message["data"])
    finally:
        await pubsub.unsubscribe(_channel(job_id))
        await r.aclose()
