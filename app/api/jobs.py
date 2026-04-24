"""FastAPI routes for jobs and WebSocket."""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request, Response, WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel
from supabase import Client

from app.api.deps import get_supabase
from app.core.logging import get_logger, safe_log
from app.domain.state_machine import InvalidStateTransitionError as DomainInvalidStateTransitionError
from app.domain.state_machine import job_state_machine
from app.infrastructure.http_exceptions import (
    InvalidStateTransitionError,
    JobNotFoundError,
    TemplateNotFoundError,
)
from app.infrastructure.security import redact_sensitive_fields
from app.domain.validation_schemas import JobCreateRequest
from app.models.job import JobCreate, JobResponse
from app.services import job_service
from app.services.job_creation_service import create_job as create_job_service
from app.services.job_creation_service import merge_template
from app.services.progress import get_snapshot, subscribe_progress
from app.services.token_tracker import get_job_usage

log = get_logger(__name__)

router = APIRouter(prefix="/v1", tags=["jobs"])
jobs_router = APIRouter(prefix="/jobs", tags=["jobs"])


class CreateJobRequest(BaseModel):
    config: dict = {}
    template_id: str | None = None
    notification_email: str | None = None




@router.post("/jobs", status_code=status.HTTP_201_CREATED, response_model=JobResponse)
async def create_job(
    body: JobCreateRequest,
    request: Request,
    supabase: Client = Depends(get_supabase),
) -> JobResponse:
    channel = request.app.state.amqp_channel

    result = await create_job_service(
        request=body,
        supabase=supabase,
        channel=channel,
        email=body.notification_email,
    )

    base_url = str(request.base_url).rstrip("/")
    return JobResponse.from_job_id(result.job_id, base_url)


@jobs_router.post("", status_code=status.HTTP_201_CREATED)
async def create_job_with_template(
    body: CreateJobRequest,
    request: Request,
    supabase: Client = Depends(get_supabase),
) -> dict:
    """Submit a new job, optionally merging a template config."""
    channel = request.app.state.amqp_channel

    if body.template_id:
        template_result = (
            supabase
            .table("job_templates")
            .select("config")
            .eq("id", body.template_id)
            .single()
            .execute()
        )
        if not template_result.data:
            raise TemplateNotFoundError(body.template_id)

        # Merge template config with overrides
        # Start with template config, apply overrides from body.config
        merged_config = {**template_result.data["config"], **body.config}
        merged_request = JobCreateRequest(**merged_config)
    else:
        # No template, validate body.config directly as JobCreateRequest
        merged_request = JobCreateRequest(**body.config)

    result = await create_job_service(
        request=merged_request,
        supabase=supabase,
        channel=channel,
        email=body.notification_email or merged_request.notification_email,
    )

    safe_log(logging.INFO, "api.job.created", job_id=result.job_id, has_template=body.template_id is not None)
    return {"id": result.job_id, "status": "queued"}


@router.get("/jobs/{job_id}")
async def get_job(
    job_id: str,
    supabase: Client = Depends(get_supabase),
) -> dict:
    job = job_service.get_job(supabase, job_id)
    if job is None:
        raise JobNotFoundError(job_id)
    return job


@router.get("/jobs/{job_id}/tokens")
async def get_job_tokens(
    job_id: str,
    supabase: Client = Depends(get_supabase),
) -> dict:
    job_service.get_job_or_404(supabase, job_id)
    return get_job_usage(job_id)


@router.get("/jobs")
async def list_jobs(
    supabase: Client = Depends(get_supabase),
    status: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
) -> dict:
    """List jobs with optional status filter and pagination."""
    offset = (page - 1) * limit
    query = supabase.table("jobs").select(
        "id,status,created_at,updated_at,config", count="exact"
    )
    if status:
        query = query.eq("status", status)
    result = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
    return {
        "jobs": [redact_sensitive_fields(job) for job in result.data],
        "total": result.count or 0,
        "page": page,
        "limit": limit,
    }


@router.patch("/jobs/{job_id}/pause")
async def pause_job(
    job_id: str,
    supabase: Client = Depends(get_supabase),
) -> dict:
    """Pause a running job. Returns 409 if the transition is not allowed."""
    job = job_service.get_job_or_404(supabase, job_id)
    try:
        job_state_machine.validate_transition(job["status"], "paused")
    except DomainInvalidStateTransitionError as exc:
        raise InvalidStateTransitionError(
            current=exc.current,
            target=exc.target,
            valid_transitions=exc.valid_transitions,
        ) from exc
    supabase.table("jobs").update({"status": "paused"}).eq("id", job_id).execute()
    log.info("api.job.paused", job_id=job_id)
    return {"id": job_id, "status": "paused"}


@router.patch("/jobs/{job_id}/resume")
async def resume_job(
    job_id: str,
    supabase: Client = Depends(get_supabase),
) -> dict:
    """Resume a paused job by setting status back to queued. Returns 409 if not allowed."""
    job = job_service.get_job_or_404(supabase, job_id)
    try:
        job_state_machine.validate_transition(job["status"], "queued")
    except DomainInvalidStateTransitionError as exc:
        raise InvalidStateTransitionError(
            current=exc.current,
            target=exc.target,
            valid_transitions=exc.valid_transitions,
        ) from exc
    supabase.table("jobs").update({"status": "queued"}).eq("id", job_id).execute()
    log.info("api.job.resumed", job_id=job_id)
    return {"id": job_id, "status": "queued"}


@router.delete("/jobs/{job_id}", status_code=204)
async def cancel_job(
    job_id: str,
    supabase: Client = Depends(get_supabase),
) -> Response:
    """Cancel a job. Returns 204 No Content."""
    job_service.get_job_or_404(supabase, job_id)
    supabase.table("jobs").update({"status": "cancelled"}).eq("id", job_id).execute()
    log.info("api.job.cancelled", job_id=job_id)
    return Response(status_code=204)


@router.post("/jobs/{job_id}/restart", status_code=201)
async def restart_job(
    job_id: str,
    supabase: Client = Depends(get_supabase),
) -> dict:
    """Create a new queued job cloned from the given job's config."""
    job = job_service.get_job_or_404(supabase, job_id)
    new_job = supabase.table("jobs").insert(
        {
            "config": job["config"],
            "status": "queued",
            "notification_email": job.get("notification_email"),
        }
    ).execute()
    new_job_id = new_job.data[0]["id"]
    log.info("api.job.restarted", original_job_id=job_id, new_job_id=new_job_id)
    return {"new_job_id": new_job_id}


@router.websocket("/ws/{job_id}")
async def websocket_endpoint(websocket: WebSocket, job_id: str) -> None:
    await websocket.accept()
    try:
        # Send the latest snapshot immediately so the client doesn't miss past progress
        snapshot = await get_snapshot(job_id)
        if snapshot:
            await websocket.send_json(snapshot)
        # Stream live progress events from Redis pub/sub
        async for event in subscribe_progress(job_id):
            await websocket.send_json(event)
    except WebSocketDisconnect:
        pass
