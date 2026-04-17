"""Chapter CRUD operations."""
from __future__ import annotations

import logging

from supabase import Client

logger = logging.getLogger(__name__)


def list_chapters(supabase: Client, job_id: str) -> list[dict]:
    result = supabase.table("chapters").select("*").eq("job_id", job_id).order("index").execute()
    return result.data or []


def update_chapter_content(supabase: Client, chapter_id: str, content: str) -> dict | None:
    """Update content of an unlocked chapter. Returns updated chapter or None if locked."""
    # Fetch current status
    current = supabase.table("chapters").select("status").eq("id", chapter_id).single().execute()
    if not current.data:
        return None
    if current.data["status"] == "locked":
        return None  # Caller raises 409
    result = supabase.table("chapters").update({"content": content}).eq("id", chapter_id).execute()
    return result.data[0] if result.data else None


def lock_chapter(supabase: Client, chapter_id: str) -> dict | None:
    result = supabase.table("chapters").update({"status": "locked"}).eq("id", chapter_id).execute()
    return result.data[0] if result.data else None


def get_artifact_path(supabase: Client, job_id: str, artifact_type: str = "bundle") -> str | None:
    result = (
        supabase.table("artifacts")
        .select("storage_path")
        .eq("job_id", job_id)
        .eq("artifact_type", artifact_type)
        .single()
        .execute()
    )
    return result.data["storage_path"] if result.data else None
