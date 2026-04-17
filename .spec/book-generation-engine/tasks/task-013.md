---
task: 013
feature: book-generation-engine
status: pending
model: haiku
supervisor: software-cto
agent: web-backend-expert
depends_on: [012]
---

# Task 013: FastAPI Backend — Chapters and Export

## Skills
- .kit/skills/frameworks-backend/python-fastapi-development/SKILL.md
- .kit/skills/languages/python-patterns/SKILL.md

## Agents
- @web-backend-expert

## Commands
- /task-handoff

> Load the skills, agents, and commands listed above before reading anything else.

---

## Objective

Implement `app/api/chapters.py` and `app/api/export.py` for chapter CRUD (list, update, lock, regenerate) and export (signed bundle URL). Also implement `app/services/chapter_service.py` and `app/services/storage_service.py` (app-side).

---

## Files

### Create
| File | Purpose |
|------|---------|
| `app/models/chapter.py` | Chapter, ChapterUpdate Pydantic models |
| `app/services/chapter_service.py` | Chapter CRUD operations |
| `app/services/storage_service.py` | get_signed_url() for export |
| `app/api/chapters.py` | Chapter + export routes |

### Modify
| File | What to change |
|------|---------------|
| `app/main.py` | Add `app.include_router(chapters_router)` after existing include |

---

## Dependencies

```bash
# No new packages.
```

---

## Code Templates

### `app/models/chapter.py` (create this file exactly)
```python
"""Chapter Pydantic models."""
from __future__ import annotations

from pydantic import BaseModel


class ChapterResponse(BaseModel):
    id: str
    job_id: str
    index: int
    title: str | None = None
    content: str
    status: str
    memory_snapshot: dict


class ChapterUpdate(BaseModel):
    content: str
```

### `app/services/chapter_service.py` (create this file exactly)
```python
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
```

### `app/services/storage_service.py` (create this file exactly)
```python
"""Storage service for signed URL generation (app-side)."""
from __future__ import annotations

from supabase import Client

BUCKET = "book-artifacts"
SIGNED_URL_EXPIRY = 604800  # 7 days


def get_signed_url(supabase: Client, storage_path: str) -> str:
    response = supabase.storage.from_(BUCKET).create_signed_url(storage_path, SIGNED_URL_EXPIRY)
    return response["signedURL"]
```

### `app/api/chapters.py` (create this file exactly)
```python
"""Chapter and export API routes."""
from __future__ import annotations

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
    from app.queue.publisher import publish_job
    # Publish a minimal regenerate event — worker handles it
    import json
    import aio_pika
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
        "files": ["manuscript.epub", "manuscript.pdf", "cover.jpg", "cover-brief.txt", "description.txt", "metadata.json"],
    }
```

### `app/main.py` (before → after — add chapters router)

**Before:**
```python
app.include_router(jobs_router)
```

**After:**
```python
from app.api.chapters import router as chapters_router

app.include_router(jobs_router)
app.include_router(chapters_router)
```

---

## Codebase Context

### Key Code Snippets
```python
# app/services/chapter_service.py — update_chapter_content returns None when locked
def update_chapter_content(supabase, chapter_id, content) -> dict | None:
    # Returns None if chapter status == "locked" or not found
    ...
```

### Key Patterns in Use
- **409 Conflict for locked chapter edits:** `PUT /chapters/{id}` returns HTTP 409 when `update_chapter_content` returns `None` due to locked status.
- **202 Accepted for regenerate:** Regenerate is async — return immediately after publishing to queue.
- **Export requires job status == "complete":** Return HTTP 400 if job is not complete.

### Architecture Decisions Affecting This Task
- Requirement 10: "WHEN the author edits a chapter inline THEN the system SHALL save the edit to Supabase on blur."
- Requirement 11: "WHEN the author clicks download THEN the system SHALL redirect to the signed Supabase Storage URL."
- `GET /v1/jobs/{id}/export` does not redirect — it returns the signed URL as JSON for the frontend to trigger the download.

---

## Handoff from Previous Task

**Files changed by previous task:** `app/config.py`, `app/models/job.py`, `app/ws/manager.py`, `app/services/job_service.py`, `app/api/jobs.py`, `app/main.py`.
**Decisions made:** App state pattern for supabase + amqp_channel. UUID job IDs. 404 for missing jobs.
**Context for this task:** Jobs + WebSocket API done. Now add chapters + export routes.
**Open questions left:** _(none)_

---

## Implementation Steps

1. Create `app/models/chapter.py` — paste template exactly.
2. Create `app/services/chapter_service.py` — paste template exactly.
3. Create `app/services/storage_service.py` — paste template exactly.
4. Create `app/api/chapters.py` — paste template exactly.
5. Edit `app/main.py` — apply before → after replacement to add chapters router.
6. Run: `ruff check app/api/chapters.py app/services/chapter_service.py` — verify zero lint errors.

---

## Decision Rules

| Scenario | Action |
|----------|--------|
| `PUT /chapters/{id}` — chapter is locked | Return HTTP 409 with `{"detail": "Chapter is locked or not found. Unlock before editing."}` |
| `PUT /chapters/{id}` — chapter not found | Return HTTP 409 (same handler — `update_chapter_content` returns None for both) |
| `GET /jobs/{id}/export` — job status != "complete" | Return HTTP 400 with `{"detail": "Job is not complete yet"}` |
| `GET /jobs/{id}/export` — bundle artifact not found | Return HTTP 404 with `{"detail": "Bundle artifact not found"}` |

---

## Acceptance Criteria

- [ ] WHEN `GET /v1/jobs/{id}/chapters` is called THEN returns list of chapters ordered by index
- [ ] WHEN `PUT /v1/chapters/{id}` is called on a locked chapter THEN returns HTTP 409
- [ ] WHEN `GET /v1/jobs/{id}/export` is called on a non-complete job THEN returns HTTP 400
- [ ] WHEN `GET /v1/jobs/{id}/export` is called on a complete job THEN returns signed URL and file list
- [ ] WHEN `ruff check app/` runs THEN zero errors

---

## Handoff to Next Task

**Files changed:** _(fill via /task-handoff)_
**Decisions made:** _(fill via /task-handoff)_
**Context for next task:** _(fill via /task-handoff)_
**Open questions:** _(fill via /task-handoff)_
