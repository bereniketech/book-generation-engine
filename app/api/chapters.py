"""Chapter and export API routes."""
from __future__ import annotations

import json

import aio_pika
from fastapi import APIRouter, HTTPException, Request, status

from app.models.chapter import ChapterResponse, ChapterUpdate
from app.services import chapter_service, storage_service

router = APIRouter(prefix="/v1", tags=["chapters"])


@router.get("/jobs/{job_id}/chapters", response_model=list[ChapterResponse])
async def list_chapters(job_id: str, request: Request) -> list[ChapterResponse]:
    supabase = request.app.state.supabase
    chapters = chapter_service.list_chapters(supabase, job_id)
    return [ChapterResponse(**ch) for ch in chapters]


@router.put("/chapters/{chapter_id}")
async def update_chapter(chapter_id: str, body: ChapterUpdate, request: Request) -> dict:
    supabase = request.app.state.supabase
    updated = chapter_service.update_chapter_content(supabase, chapter_id, body.content)
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Chapter is locked or not found. Unlock before editing.",
        )
    return updated


@router.post("/chapters/{chapter_id}/lock")
async def lock_chapter(chapter_id: str, request: Request) -> dict:
    supabase = request.app.state.supabase
    result = chapter_service.lock_chapter(supabase, chapter_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Chapter not found")
    return result


@router.post("/chapters/{chapter_id}/regenerate", status_code=status.HTTP_202_ACCEPTED)
async def regenerate_chapter(chapter_id: str, request: Request) -> dict:
    """Publish a regenerate task to RabbitMQ. Returns 202 Accepted."""
    channel = request.app.state.amqp_channel
    payload = json.dumps({"type": "regenerate_chapter", "chapter_id": chapter_id})
    await channel.default_exchange.publish(
        aio_pika.Message(body=payload.encode(), delivery_mode=aio_pika.DeliveryMode.PERSISTENT),
        routing_key="book_jobs",
    )
    return {"accepted": True, "chapter_id": chapter_id}


@router.get("/jobs/{job_id}/export")
async def get_export(job_id: str, request: Request) -> dict:
    supabase = request.app.state.supabase
    # Verify job is complete
    job_result = supabase.table("jobs").select("status").eq("id", job_id).single().execute()
    if not job_result.data:
        raise HTTPException(status_code=404, detail="Job not found")
    if job_result.data["status"] != "complete":
        raise HTTPException(status_code=400, detail="Job is not complete yet")
    path = chapter_service.get_artifact_path(supabase, job_id, "bundle")
    if not path:
        raise HTTPException(status_code=404, detail="Bundle artifact not found")
    signed_url = storage_service.get_signed_url(supabase, path)
    return {
        "job_id": job_id,
        "download_url": signed_url,
        "files": [
            "manuscript.epub",
            "manuscript.pdf",
            "cover.jpg",
            "cover-brief.txt",
            "description.txt",
            "metadata.json",
        ],
    }
