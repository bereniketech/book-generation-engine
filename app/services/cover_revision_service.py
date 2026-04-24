"""Cover revision service for managing revision audit trail."""
from __future__ import annotations

import logging
from typing import Optional

from supabase import Client

logger = logging.getLogger(__name__)


async def add_revision(supabase: Client, job_id: str, feedback: str) -> dict:
    """
    Insert a new cover revision record with auto-incremented revision number.

    Args:
        supabase: Supabase client
        job_id: Job UUID
        feedback: User feedback text

    Returns:
        The inserted revision record dict with keys: id, job_id, feedback, requested_at, revision_number
    """
    # Get the next revision number by counting existing revisions for this job
    result = supabase.table("cover_revisions").select("revision_number", count="exact").eq("job_id", job_id).execute()
    next_revision_number = (result.count or 0) + 1

    # Insert the new revision
    insert_result = supabase.table("cover_revisions").insert({
        "job_id": job_id,
        "feedback": feedback,
        "revision_number": next_revision_number,
    }).execute()

    if not insert_result.data:
        logger.error("Failed to insert cover revision for job %s", job_id)
        raise ValueError(f"Failed to insert cover revision for job {job_id}")

    revision = insert_result.data[0]
    logger.info(
        "cover_revision.created",
        job_id=job_id,
        revision_number=next_revision_number,
        feedback_length=len(feedback),
    )
    return revision


async def get_latest_revision(supabase: Client, job_id: str) -> Optional[dict]:
    """
    Retrieve the most recent cover revision for a job.

    Args:
        supabase: Supabase client
        job_id: Job UUID

    Returns:
        The latest revision record dict or None if no revisions exist
    """
    result = (
        supabase.table("cover_revisions")
        .select("*")
        .eq("job_id", job_id)
        .order("revision_number", desc=True)
        .limit(1)
        .execute()
    )

    if not result.data:
        return None

    return result.data[0]


async def get_all_revisions(supabase: Client, job_id: str) -> list[dict]:
    """
    Retrieve all cover revisions for a job, ordered by revision number descending.

    Args:
        supabase: Supabase client
        job_id: Job UUID

    Returns:
        List of revision records
    """
    result = (
        supabase.table("cover_revisions")
        .select("*")
        .eq("job_id", job_id)
        .order("revision_number", desc=True)
        .execute()
    )

    return result.data or []
