"""Chapter editing API endpoints."""
from __future__ import annotations

from pydantic import BaseModel
from fastapi import APIRouter, Depends
from supabase import Client

from app.api.deps import get_supabase
from app.core.logging import get_logger
from app.domain.constants import CHAPTER_PREVIEW_CHARS
from app.infrastructure.http_exceptions import ChapterNotFoundError
from app.infrastructure.security import redact_sensitive_fields

log = get_logger(__name__)

router = APIRouter(prefix="/jobs", tags=["chapters"])


class ChapterEditRequest(BaseModel):
    content: str


def _truncate_at_word_boundary(text: str, max_chars: int) -> str:
    """Truncate text at character limit with word-boundary awareness.

    If the text exceeds max_chars, finds the last space within the limit
    and truncates there. Appends … to indicate truncation.
    If there's no space within the limit, truncates at the limit anyway.
    """
    if len(text) <= max_chars:
        return text

    # Truncate to max_chars and look backwards for the last space
    truncated = text[:max_chars]
    last_space = truncated.rfind(" ")

    if last_space > 0:
        # Found a space; truncate there
        return truncated[:last_space] + "…"
    else:
        # No space found; truncate at limit
        return truncated + "…"


@router.get("/{job_id}/chapters")
async def list_chapters(
    job_id: str,
    supabase: Client = Depends(get_supabase),
):
    """List all chapters for a job with status and content preview."""
    result = (
        supabase
        .table("chapters")
        .select("index,status,qa_score,content")
        .eq("job_id", job_id)
        .order("index")
        .execute()
    )
    chapters = [
        redact_sensitive_fields({
            "index": ch["index"],
            "status": ch["status"],
            "qa_score": ch.get("qa_score"),
            "content_preview": _truncate_at_word_boundary(ch.get("content") or "", CHAPTER_PREVIEW_CHARS),
        })
        for ch in result.data
    ]
    return {"chapters": chapters}


@router.get("/{job_id}/chapters/{index}")
async def get_chapter(
    job_id: str,
    index: int,
    supabase: Client = Depends(get_supabase),
):
    """Get full chapter content with status and readability scores."""
    result = (
        supabase
        .table("chapters")
        .select("index,content,status,qa_score,flesch_kincaid_grade,flesch_reading_ease")
        .eq("job_id", job_id)
        .eq("index", index)
        .single()
        .execute()
    )
    if not result.data:
        raise ChapterNotFoundError(job_id, index)
    return redact_sensitive_fields({"job_id": job_id, **result.data})


@router.patch("/{job_id}/chapters/{index}")
async def edit_chapter(
    job_id: str,
    index: int,
    body: ChapterEditRequest,
    supabase: Client = Depends(get_supabase),
):
    """Update chapter content and set status to locked."""
    result = (
        supabase
        .table("chapters")
        .select("id")
        .eq("job_id", job_id)
        .eq("index", index)
        .single()
        .execute()
    )
    if not result.data:
        raise ChapterNotFoundError(job_id, index)
    supabase.table("chapters").update({
        "content": body.content,
        "status": "locked",
    }).eq("job_id", job_id).eq("index", index).execute()
    log.info("chapter.edited", job_id=job_id, chapter_index=index)
    return {"job_id": job_id, "index": index, "status": "locked"}
