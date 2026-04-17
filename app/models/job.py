"""Pydantic models for job API."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class LLMProviderConfig(BaseModel):
    provider: Literal["anthropic", "openai", "google", "ollama", "openai-compatible"]
    model: str = Field(min_length=1, max_length=200)
    api_key: str = Field(min_length=1, max_length=500)
    base_url: str | None = None


class ImageProviderConfig(BaseModel):
    provider: Literal["dall-e-3", "replicate-flux"]
    api_key: str = Field(min_length=1, max_length=500)


class JobCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    topic: str = Field(min_length=1, max_length=2000)
    mode: Literal["fiction", "non_fiction"]
    audience: str = Field(min_length=1, max_length=500)
    tone: str = Field(min_length=1, max_length=200)
    target_chapters: int = Field(ge=3, le=50, default=12)
    llm: LLMProviderConfig
    image: ImageProviderConfig
    notification_email: str | None = None


class JobResponse(BaseModel):
    job_id: str
    status: str
    ws_url: str

    @classmethod
    def from_job_id(cls, job_id: str, base_url: str) -> JobResponse:
        return cls(
            job_id=job_id,
            status="queued",
            ws_url=f"{base_url}/v1/ws/{job_id}",
        )
