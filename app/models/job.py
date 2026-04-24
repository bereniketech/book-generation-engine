"""Pydantic models for job API.

LLMProviderConfig, ImageProviderConfig, and JobCreate (aka JobCreateRequest)
are the single-source-of-truth models defined in app.domain.validation_schemas.
This module re-exports them for backwards-compatibility with existing imports.
"""
from __future__ import annotations

from pydantic import BaseModel

# Re-export canonical validation models so all importers use one definition.
from app.domain.validation_schemas import (  # noqa: F401
    ImageProviderConfig,
    JobCreateRequest,
    LLMProviderConfig,
)

# Alias: existing code imports JobCreate; map it to the canonical name.
JobCreate = JobCreateRequest


class JobResponse(BaseModel):
    job_id: str
    status: str
    ws_url: str

    @classmethod
    def from_job_id(cls, job_id: str, base_url: str) -> "JobResponse":
        return cls(
            job_id=job_id,
            status="queued",
            ws_url=f"{base_url}/v1/ws/{job_id}",
        )
