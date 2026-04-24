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
