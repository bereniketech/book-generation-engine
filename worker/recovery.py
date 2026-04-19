"""Job recovery: on worker startup, re-enqueue stale generating jobs."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone, timedelta

import aio_pika
from supabase import create_client

from app.core.logging import get_logger

log = get_logger(__name__)

SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY: str = os.getenv("SUPABASE_SERVICE_KEY", "")
STALE_JOB_TIMEOUT: int = int(os.getenv("STALE_JOB_TIMEOUT", "300"))  # seconds


async def scan_and_recover(channel: aio_pika.abc.AbstractChannel) -> int:
    """Scan for stale generating jobs and re-enqueue them.

    Returns the count of recovered jobs.
    Called once at worker startup before entering the main consumer loop.
    """
    client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    cutoff = (datetime.now(timezone.utc) - timedelta(seconds=STALE_JOB_TIMEOUT)).isoformat()

    stale_jobs = (
        client.table("jobs")
        .select("id,config,updated_at")
        .eq("status", "generating")
        .lt("updated_at", cutoff)
        .execute()
        .data
    )

    if not stale_jobs:
        log.info("worker.recovery.scan", stale_count=0)
        return 0

    recovered = 0
    exchange = await channel.get_exchange("", ensure=False)

    for job in stale_jobs:
        job_id = job["id"]
        try:
            locked_chapters = (
                client.table("chapters")
                .select("index")
                .eq("job_id", job_id)
                .eq("status", "locked")
                .order("index", desc=True)
                .limit(1)
                .execute()
                .data
            )
            cursor = locked_chapters[0]["index"] + 1 if locked_chapters else 0

            client.table("jobs").update({
                "status": "queued",
                "chapter_cursor": cursor,
            }).eq("id", job_id).execute()

            payload = {**job["config"], "job_id": job_id, "chapter_cursor": cursor}
            await exchange.publish(
                aio_pika.Message(
                    body=json.dumps(payload).encode(),
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                ),
                routing_key="bookgen.jobs",
            )

            log.info(
                "worker.recovery.found",
                job_id=job_id,
                stale_since=job["updated_at"],
                chapter_cursor=cursor,
            )
            recovered += 1

        except Exception as exc:
            log.error("worker.recovery.job_failed", job_id=job_id, error=str(exc))

    log.info("worker.recovery.complete", recovered=recovered, total_stale=len(stale_jobs))
    return recovered
