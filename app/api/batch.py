"""Batch job submission API."""
from __future__ import annotations

import asyncio
import csv
import io
import json
import os
import uuid
from typing import Any

import aio_pika
from fastapi import APIRouter, Body, Depends, UploadFile, File
from pydantic import BaseModel, ValidationError
from supabase import Client

from app.api.deps import get_supabase
from app.core.logging import get_logger
from app.infrastructure.http_exceptions import EmptyBatchError

log = get_logger(__name__)

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
MAX_PARALLEL_JOBS = int(os.getenv("MAX_PARALLEL_JOBS", "10"))
BATCH_THROTTLE_DELAY = float(os.getenv("BATCH_THROTTLE_DELAY", "0.5"))

router = APIRouter(prefix="/batch", tags=["batch"])


class JobConfigSchema(BaseModel):
    """Minimal job config validation."""
    title: str
    genre: str


class BatchJsonRequest(BaseModel):
    format: str = "json"
    jobs: list[dict[str, Any]]


async def _active_job_count(supabase: Client) -> int:
    """Count jobs currently queued or generating."""
    result = (
        supabase
        .table("jobs")
        .select("id", count="exact")
        .in_("status", ["queued", "generating"])
        .execute()
    )
    return result.count or 0


async def _enqueue_job(channel: aio_pika.abc.AbstractChannel, job_id: str, config: dict) -> None:
    exchange = await channel.get_exchange("", ensure=False)
    payload = {**config, "job_id": job_id}
    await exchange.publish(
        aio_pika.Message(
            body=json.dumps(payload).encode(),
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        ),
        routing_key="bookgen.jobs",
    )


@router.post("")
async def submit_batch(
    request: BatchJsonRequest = Body(...),
    supabase: Client = Depends(get_supabase),
):
    """Submit a batch of jobs from a JSON payload."""
    batch_id = str(uuid.uuid4())
    job_ids: list[str] = []
    errors: list[dict] = []

    connection = await aio_pika.connect_robust(RABBITMQ_URL)
    channel = await connection.channel()

    try:
        for row_idx, raw_config in enumerate(request.jobs):
            try:
                validated = JobConfigSchema(**raw_config)
                config = validated.model_dump()
            except (ValidationError, Exception) as exc:
                errors.append({"row": row_idx, "reason": str(exc)})
                log.warning("batch.row.skipped", batch_id=batch_id, row=row_idx, reason=str(exc))
                continue

            # Throttle: wait if too many active jobs
            while await _active_job_count(supabase) >= MAX_PARALLEL_JOBS:
                log.info("batch.throttle.waiting", batch_id=batch_id, active=await _active_job_count(supabase))
                await asyncio.sleep(BATCH_THROTTLE_DELAY)

            # Insert job record
            job_result = supabase.table("jobs").insert({
                "config": config,
                "status": "queued",
                "batch_id": batch_id,
            }).execute()
            job_id = job_result.data[0]["id"]

            await _enqueue_job(channel, job_id, config)
            job_ids.append(job_id)
            log.info("batch.job.enqueued", batch_id=batch_id, job_id=job_id, row=row_idx)

    finally:
        await connection.close()

    if not job_ids:
        raise EmptyBatchError()

    log.info("batch.complete", batch_id=batch_id, enqueued=len(job_ids), skipped=len(errors))
    return {
        "batch_id": batch_id,
        "enqueued": len(job_ids),
        "skipped": len(errors),
        "job_ids": job_ids,
        "errors": errors,
    }


@router.post("/csv")
async def submit_batch_csv(
    file: UploadFile = File(...),
    supabase: Client = Depends(get_supabase),
):
    """Submit a batch of jobs from a CSV file upload."""
    contents = await file.read()
    text = contents.decode("utf-8")
    reader = csv.DictReader(io.StringIO(text))
    jobs = [dict(row) for row in reader]

    return await submit_batch(BatchJsonRequest(format="csv", jobs=jobs), supabase)
