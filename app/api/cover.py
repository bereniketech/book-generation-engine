"""Cover approval flow API endpoints."""
from __future__ import annotations

import os
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException
from supabase import create_client

from app.core.logging import get_logger

log = get_logger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")

router = APIRouter(prefix="/jobs", tags=["cover"])


def _client():
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def _get_job_or_404(job_id: str) -> dict:
    result = _client().table("jobs").select("id,status,cover_status,cover_url,config").eq("id", job_id).single().execute()
    if not result.data:
        raise HTTPException(status_code=404, detail={"error": "Job not found", "code": "JOB_NOT_FOUND"})
    return result.data


class ReviseRequest(BaseModel):
    feedback: str


@router.get("/{job_id}/cover")
async def get_cover(job_id: str):
    job = _get_job_or_404(job_id)
    return {
        "job_id": job_id,
        "cover_url": job.get("cover_url"),
        "cover_status": job.get("cover_status"),
    }


@router.post("/{job_id}/cover/approve")
async def approve_cover(job_id: str):
    job = _get_job_or_404(job_id)
    if job.get("cover_status") != "awaiting_approval":
        raise HTTPException(
            status_code=409,
            detail={"error": "No cover awaiting approval", "code": "NO_PENDING_COVER"},
        )
    _client().table("jobs").update({
        "cover_status": "approved",
        "status": "assembling",
    }).eq("id", job_id).execute()
    log.info("cover.approved", job_id=job_id)
    return {"job_id": job_id, "status": "assembling"}


@router.post("/{job_id}/cover/revise")
async def revise_cover(job_id: str, body: ReviseRequest):
    job = _get_job_or_404(job_id)
    if job.get("cover_status") != "awaiting_approval":
        raise HTTPException(
            status_code=409,
            detail={"error": "No cover awaiting approval", "code": "NO_PENDING_COVER"},
        )
    config = job.get("config", {})
    config["cover_revision_feedback"] = body.feedback
    _client().table("jobs").update({
        "cover_status": "revising",
        "status": "generating",
        "config": config,
    }).eq("id", job_id).execute()
    log.info("cover.revision_requested", job_id=job_id, feedback_length=len(body.feedback))
    return {"job_id": job_id, "cover_status": "revising"}
