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
