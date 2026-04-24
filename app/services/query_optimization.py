"""Query optimization patterns and utilities.

Provides guidelines and utilities to prevent common database query anti-patterns:
- N+1 queries (multiple queries for related data)
- Overfetching (requesting more columns than needed)
- Inefficient filtering (post-query filtering instead of SQL)
"""
from __future__ import annotations

from typing import Any

from app.core.logging import get_logger

log = get_logger(__name__)


def batch_jobs_by_id(supabase_client: Any, job_ids: list[str], fields: str = "*") -> dict[str, dict]:
    """Fetch multiple jobs efficiently in a single query (prevents N+1).

    Instead of:
        for job_id in job_ids:
            job = get_job(job_id)  # N queries

    Use:
        jobs = batch_jobs_by_id(supabase_client, job_ids)  # 1 query

    Args:
        supabase_client: Supabase client instance
        job_ids: List of job IDs to fetch
        fields: Comma-separated columns to select (default: all)

    Returns:
        Dict mapping job_id -> job_record. Missing IDs are excluded.

    Example:
        >>> jobs = batch_jobs_by_id(supabase, ["id1", "id2", "id3"])
        >>> job_statuses = {jid: job["status"] for jid, job in jobs.items()}
    """
    if not job_ids:
        return {}

    result = (
        supabase_client
        .table("jobs")
        .select(fields)
        .in_("id", job_ids)
        .execute()
    )
    return {job["id"]: job for job in result.data}


def batch_chapters_by_job_id(supabase_client: Any, job_id: str, fields: str = "*") -> list[dict]:
    """Fetch all chapters for a job efficiently (prevents N+1 on chapter list).

    Args:
        supabase_client: Supabase client instance
        job_id: Job ID
        fields: Comma-separated columns to select (default: all)

    Returns:
        List of chapter records for the job, ordered by index

    Example:
        >>> chapters = batch_chapters_by_job_id(supabase, job_id)
        >>> chapter_count = len(chapters)
    """
    result = (
        supabase_client
        .table("chapters")
        .select(fields)
        .eq("job_id", job_id)
        .order("index", desc=False)
        .execute()
    )
    return result.data


def select_minimal_fields(fields_needed: list[str]) -> str:
    """Build efficient column selection string (prevents overfetching).

    Instead of:
        query.select("*")  # fetches 50+ columns

    Use:
        fields = select_minimal_fields(["id", "status", "created_at"])
        query.select(fields)  # fetches only 3 columns

    Args:
        fields_needed: List of column names to select

    Returns:
        Comma-separated field string for Supabase query

    Example:
        >>> fields = select_minimal_fields(["id", "status", "config"])
        >>> query.select(fields)
    """
    return ",".join(fields_needed)


# Common field selections for optimization
MINIMAL_JOB_FIELDS = select_minimal_fields(["id", "status", "created_at", "updated_at"])
LISTING_JOB_FIELDS = select_minimal_fields(["id", "status", "created_at", "updated_at", "config"])
COVER_JOB_FIELDS = select_minimal_fields(["id", "status", "cover_status", "cover_url", "config"])
FULL_JOB_FIELDS = "*"

# Common field selections for chapters
CHAPTER_LISTING_FIELDS = select_minimal_fields(["index", "status", "content", "qa_score"])
CHAPTER_PREVIEW_FIELDS = select_minimal_fields(["index", "status", "content_preview", "qa_score"])
