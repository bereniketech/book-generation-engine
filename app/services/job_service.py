"""Job CRUD operations against Supabase."""
from __future__ import annotations

import logging

from supabase import Client

from app.infrastructure.security import redact_sensitive_fields

logger = logging.getLogger(__name__)


def create_job(supabase: Client, job_id: str, config: dict, notification_email: str | None) -> dict:
    result = supabase.table("jobs").insert({
        "id": job_id,
        "status": "queued",
        "config": config,
        "notification_email": notification_email,
    }).execute()
    return result.data[0]


def get_job(supabase: Client, job_id: str) -> dict | None:
    result = supabase.table("jobs").select("*").eq("id", job_id).single().execute()
    if not result.data:
        return None
    return redact_sensitive_fields(result.data)


def update_job_status(supabase: Client, job_id: str, status: str) -> None:
    supabase.table("jobs").update({"status": status}).eq("id", job_id).execute()


def get_job_or_404(supabase: Client, job_id: str, fields: str = "*") -> dict:
    """Fetch job by ID or raise JobNotFoundError.

    Args:
        supabase: Supabase client instance
        job_id: Job UUID to fetch
        fields: Comma-separated list of columns to retrieve (default: all columns)

    Returns:
        Job record as dictionary with specified fields

    Raises:
        JobNotFoundError: If job with given ID does not exist

    Example:
        >>> job = get_job_or_404(supabase, "job-123")  # All fields
        >>> job = get_job_or_404(supabase, "job-123", fields="id,status,cover_status,cover_url,config")
    """
    from app.infrastructure.http_exceptions import JobNotFoundError

    result = (
        supabase
        .table("jobs")
        .select(fields)
        .eq("id", job_id)
        .single()
        .execute()
    )
    if not result.data:
        raise JobNotFoundError(job_id)
    return result.data
