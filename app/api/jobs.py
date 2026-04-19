"""FastAPI routes for jobs and WebSocket."""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request, Response, WebSocket, WebSocketDisconnect, status

from app.core.logging import get_logger
from app.models.job import JobCreate, JobResponse
from app.queue.publisher import publish_job
from app.services import job_service
from app.services.progress import get_snapshot, subscribe_progress
from app.services.token_tracker import get_job_usage

log = get_logger(__name__)

router = APIRouter(prefix="/v1", tags=["jobs"])

TERMINAL_STATES = {"complete", "cancelled"}


def _get_job_or_404(supabase, job_id: str) -> dict:
    result = supabase.table("jobs").select("*").eq("id", job_id).single().execute()
    if not result.data:
        raise HTTPException(
            status_code=404,
            detail={"error": "Job not found", "code": "JOB_NOT_FOUND"},
        )
    return result.data


@router.post("/jobs", status_code=status.HTTP_201_CREATED, response_model=JobResponse)
async def create_job(body: JobCreate, request: Request) -> JobResponse:
    supabase = request.app.state.supabase
    channel = request.app.state.amqp_channel

    job_id = str(uuid.uuid4())
    config = body.model_dump()

    job_service.create_job(
        supabase=supabase,
        job_id=job_id,
        config=config,
        notification_email=body.notification_email,
    )
    await publish_job(channel=channel, job_id=job_id, config=config)

    base_url = str(request.base_url).rstrip("/")
    return JobResponse.from_job_id(job_id, base_url)


@router.get("/jobs/{job_id}")
async def get_job(job_id: str, request: Request) -> dict:
    supabase = request.app.state.supabase
    job = job_service.get_job(supabase, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/jobs/{job_id}/tokens")
async def get_job_tokens(job_id: str, request: Request) -> dict:
    supabase = request.app.state.supabase
    _get_job_or_404(supabase, job_id)
    return get_job_usage(job_id)


@router.get("/jobs")
async def list_jobs(
    request: Request,
    status: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
) -> dict:
    """List jobs with optional status filter and pagination."""
    supabase = request.app.state.supabase
    offset = (page - 1) * limit
    query = supabase.table("jobs").select(
        "id,status,created_at,updated_at,config", count="exact"
    )
    if status:
        query = query.eq("status", status)
    result = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
    return {
        "jobs": result.data,
        "total": result.count or 0,
        "page": page,
        "limit": limit,
    }


@router.patch("/jobs/{job_id}/pause")
async def pause_job(job_id: str, request: Request) -> dict:
    """Pause a running job. Returns 409 if job is in a terminal state."""
    supabase = request.app.state.supabase
    job = _get_job_or_404(supabase, job_id)
    if job["status"] in TERMINAL_STATES:
        raise HTTPException(
            status_code=409,
            detail={
                "error": f"Cannot pause job in {job['status']} state",
                "code": "INVALID_STATE_TRANSITION",
            },
        )
    supabase.table("jobs").update({"status": "paused"}).eq("id", job_id).execute()
    log.info("api.job.paused", job_id=job_id)
    return {"id": job_id, "status": "paused"}


@router.patch("/jobs/{job_id}/resume")
async def resume_job(job_id: str, request: Request) -> dict:
    """Resume a paused job by setting status back to queued."""
    supabase = request.app.state.supabase
    _get_job_or_404(supabase, job_id)
    supabase.table("jobs").update({"status": "queued"}).eq("id", job_id).execute()
    log.info("api.job.resumed", job_id=job_id)
    return {"id": job_id, "status": "queued"}


@router.delete("/jobs/{job_id}", status_code=204)
async def cancel_job(job_id: str, request: Request) -> Response:
    """Cancel a job. Returns 204 No Content."""
    supabase = request.app.state.supabase
    _get_job_or_404(supabase, job_id)
    supabase.table("jobs").update({"status": "cancelled"}).eq("id", job_id).execute()
    log.info("api.job.cancelled", job_id=job_id)
    return Response(status_code=204)


@router.post("/jobs/{job_id}/restart", status_code=201)
async def restart_job(job_id: str, request: Request) -> dict:
    """Create a new queued job cloned from the given job's config."""
    supabase = request.app.state.supabase
    job = _get_job_or_404(supabase, job_id)
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
