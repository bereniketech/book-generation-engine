"""Job CRUD operations against Supabase."""
from __future__ import annotations

import logging

from supabase import Client

logger = logging.getLogger(__name__)


def _redact_config(config: dict) -> dict:
    """Remove API keys from config dict before returning to client."""
    safe = dict(config)
    for key in ("api_key", "llm_api_key", "image_api_key"):
        if key in safe:
            safe[key] = "***"
    if "llm" in safe and isinstance(safe["llm"], dict):
        safe["llm"] = {**safe["llm"], "api_key": "***"}
    if "image" in safe and isinstance(safe["image"], dict):
        safe["image"] = {**safe["image"], "api_key": "***"}
    return safe


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
    job = result.data
    job["config"] = _redact_config(job.get("config", {}))
    return job


def update_job_status(supabase: Client, job_id: str, status: str) -> None:
    supabase.table("jobs").update({"status": status}).eq("id", job_id).execute()
