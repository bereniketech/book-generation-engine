"""FastAPI routes for jobs and WebSocket."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect, status

from app.models.job import JobCreate, JobResponse
from app.queue.publisher import publish_job
from app.services import job_service
from app.services.progress import get_snapshot, subscribe_progress
from app.services.token_tracker import get_job_usage

router = APIRouter(prefix="/v1", tags=["jobs"])


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
async def get_job_tokens(job_id: str) -> dict:
    return get_job_usage(job_id)


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
