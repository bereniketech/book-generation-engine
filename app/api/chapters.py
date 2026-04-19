"""Chapter editing API endpoints."""
from __future__ import annotations

import os
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException
from supabase import create_client

from app.core.logging import get_logger

log = get_logger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")

router = APIRouter(prefix="/jobs", tags=["chapters"])


def _client():
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


class ChapterEditRequest(BaseModel):
    content: str


@router.get("/{job_id}/chapters")
async def list_chapters(job_id: str):
    """List all chapters for a job with status and content preview."""
    result = (
        _client()
        .table("chapters")
        .select("index,status,qa_score,content")
        .eq("job_id", job_id)
        .order("index")
        .execute()
    )
    chapters = [
        {
            "index": ch["index"],
            "status": ch["status"],
            "qa_score": ch.get("qa_score"),
            "content_preview": (ch.get("content") or "")[:200],
        }
        for ch in result.data
    ]
    return {"chapters": chapters}


@router.get("/{job_id}/chapters/{index}")
async def get_chapter(job_id: str, index: int):
    """Get full chapter content with status and readability scores."""
    result = (
        _client()
        .table("chapters")
        .select("index,content,status,qa_score,flesch_kincaid_grade,flesch_reading_ease")
        .eq("job_id", job_id)
        .eq("index", index)
        .single()
        .execute()
    )
    if not result.data:
        raise HTTPException(
            status_code=404,
            detail={"error": "Chapter not found", "code": "CHAPTER_NOT_FOUND"},
        )
    return {"job_id": job_id, **result.data}


@router.patch("/{job_id}/chapters/{index}")
async def edit_chapter(job_id: str, index: int, body: ChapterEditRequest):
    """Update chapter content and set status to locked."""
    result = (
        _client()
        .table("chapters")
        .select("id")
        .eq("job_id", job_id)
        .eq("index", index)
        .single()
        .execute()
    )
    if not result.data:
        raise HTTPException(
            status_code=404,
            detail={"error": "Chapter not found", "code": "CHAPTER_NOT_FOUND"},
        )
    _client().table("chapters").update({
        "content": body.content,
        "status": "locked",
    }).eq("job_id", job_id).eq("index", index).execute()
    log.info("chapter.edited", job_id=job_id, chapter_index=index)
    return {"job_id": job_id, "index": index, "status": "locked"}
