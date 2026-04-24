"""Cover approval flow API endpoints."""
from __future__ import annotations

from pydantic import BaseModel
from fastapi import APIRouter, Depends
from supabase import Client

from app.api.deps import get_supabase
from app.core.logging import get_logger
from app.domain.state_machine import InvalidStateTransitionError as DomainInvalidStateTransitionError
from app.domain.state_machine import cover_state_machine
from app.infrastructure.http_exceptions import (
    InvalidStateTransitionError,
    JobNotFoundError,
)
from app.infrastructure.security import redact_sensitive_fields
from app.services import cover_revision_service

log = get_logger(__name__)

router = APIRouter(prefix="/jobs", tags=["cover"])


def _get_job_or_404(supabase: Client, job_id: str) -> dict:
    result = (
        supabase
        .table("jobs")
        .select("id,status,cover_status,cover_url,config")
        .eq("id", job_id)
        .single()
        .execute()
    )
    if not result.data:
        raise JobNotFoundError(job_id)
    return result.data


def _validate_cover_transition(job: dict, target: str) -> None:
    """Validate cover status transition, mapping domain errors to HTTP exceptions."""
    current = job.get("cover_status") or ""
    try:
        cover_state_machine.validate_transition(current, target)
    except DomainInvalidStateTransitionError as exc:
        raise InvalidStateTransitionError(
            current=exc.current,
            target=exc.target,
            valid_transitions=exc.valid_transitions,
        ) from exc


class ReviseRequest(BaseModel):
    feedback: str


@router.get("/{job_id}/cover")
async def get_cover(
    job_id: str,
    supabase: Client = Depends(get_supabase),
):
    job = _get_job_or_404(supabase, job_id)
    return redact_sensitive_fields({
        "job_id": job_id,
        "cover_url": job.get("cover_url"),
        "cover_status": job.get("cover_status"),
    })


@router.post("/{job_id}/cover/approve")
async def approve_cover(
    job_id: str,
    supabase: Client = Depends(get_supabase),
):
    job = _get_job_or_404(supabase, job_id)
    _validate_cover_transition(job, "approved")
    supabase.table("jobs").update({
        "cover_status": "approved",
        "status": "assembling",
    }).eq("id", job_id).execute()
    log.info("cover.approved", job_id=job_id)
    return {"job_id": job_id, "status": "assembling"}


@router.post("/{job_id}/cover/revise")
async def revise_cover(
    job_id: str,
    body: ReviseRequest,
    supabase: Client = Depends(get_supabase),
):
    job = _get_job_or_404(supabase, job_id)
    _validate_cover_transition(job, "revising")

    # Record the revision in the audit trail
    await cover_revision_service.add_revision(supabase, job_id, body.feedback)

    # Update job status and transition cover_status (but NOT config)
    supabase.table("jobs").update({
        "cover_status": "revising",
        "status": "generating",
    }).eq("id", job_id).execute()
    log.info("cover.revision_requested", job_id=job_id, feedback_length=len(body.feedback))
    return {"job_id": job_id, "cover_status": "revising"}
