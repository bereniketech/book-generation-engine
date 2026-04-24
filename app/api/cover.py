"""Cover approval flow API endpoints."""
from __future__ import annotations

from pydantic import BaseModel
from fastapi import APIRouter

from app.core.logging import get_logger
from app.infrastructure.http_exceptions import JobNotFoundError, NoCoverAwaitingApprovalError
from app.infrastructure.supabase_client import get_supabase_client

log = get_logger(__name__)

router = APIRouter(prefix="/jobs", tags=["cover"])


def _get_job_or_404(job_id: str) -> dict:
    result = get_supabase_client().table("jobs").select("id,status,cover_status,cover_url,config").eq("id", job_id).single().execute()
    if not result.data:
        raise JobNotFoundError(job_id)
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
        raise NoCoverAwaitingApprovalError()
    get_supabase_client().table("jobs").update({
        "cover_status": "approved",
        "status": "assembling",
    }).eq("id", job_id).execute()
    log.info("cover.approved", job_id=job_id)
    return {"job_id": job_id, "status": "assembling"}


@router.post("/{job_id}/cover/revise")
async def revise_cover(job_id: str, body: ReviseRequest):
    job = _get_job_or_404(job_id)
    if job.get("cover_status") != "awaiting_approval":
        raise NoCoverAwaitingApprovalError()
    config = job.get("config", {})
    config["cover_revision_feedback"] = body.feedback
    get_supabase_client().table("jobs").update({
        "cover_status": "revising",
        "status": "generating",
        "config": config,
    }).eq("id", job_id).execute()
    log.info("cover.revision_requested", job_id=job_id, feedback_length=len(body.feedback))
    return {"job_id": job_id, "cover_status": "revising"}
