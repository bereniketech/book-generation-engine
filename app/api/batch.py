"""Batch job submission API."""
from __future__ import annotations

import asyncio
import csv
import io
import os
import uuid
from typing import Any

import aio_pika
from fastapi import APIRouter, Body, Depends, UploadFile, File
from pydantic import BaseModel
from supabase import Client

from app.api.deps import get_supabase
from app.core.logging import get_logger
from app.infrastructure.http_exceptions import EmptyBatchError
from app.services.job_creation_service import create_job as create_job_service
from app.services.job_creation_service import validate_job_request

log = get_logger(__name__)

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
MAX_PARALLEL_JOBS = int(os.getenv("MAX_PARALLEL_JOBS", "10"))
BATCH_THROTTLE_DELAY = float(os.getenv("BATCH_THROTTLE_DELAY", "0.5"))

router = APIRouter(prefix="/batch", tags=["batch"])


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


@router.post("")
async def submit_batch(
    request: BatchJsonRequest = Body(...),
    supabase: Client = Depends(get_supabase),
):
    """Submit a batch of jobs from a JSON payload.

    Each row is validated against JobCreateRequest. Invalid rows are rejected with
    per-row error details; only valid rows are enqueued.
    """
    batch_id = str(uuid.uuid4())
    job_ids: list[str] = []
    errors: list[dict] = []

    connection = await aio_pika.connect_robust(RABBITMQ_URL)
    channel = await connection.channel()

    try:
        for row_idx, raw_config in enumerate(request.jobs):
            # Validate each row against full JobCreateRequest schema
            validated_request, validation_errors = validate_job_request(raw_config)

            if validation_errors:
                errors.append({"row": row_idx, "errors": validation_errors})
                log.warning("batch.row.validation.failed", batch_id=batch_id, row=row_idx, errors=validation_errors)
                continue

            # Throttle: wait if too many active jobs
            while await _active_job_count(supabase) >= MAX_PARALLEL_JOBS:
                log.info("batch.throttle.waiting", batch_id=batch_id, active=await _active_job_count(supabase))
                await asyncio.sleep(BATCH_THROTTLE_DELAY)

            # Create job using the centralized service
            result = await create_job_service(
                request=validated_request,
                supabase=supabase,
                channel=channel,
                email=validated_request.notification_email,
            )

            # Update job record with batch_id (already created in create_job_service)
            supabase.table("jobs").update({"batch_id": batch_id}).eq("id", result.job_id).execute()

            job_ids.append(result.job_id)
            log.info("batch.job.enqueued", batch_id=batch_id, job_id=result.job_id, row=row_idx)

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
