"""Centralized validation schemas for job creation.

Constraints here MUST match frontend/lib/validation.ts exactly.
When changing limits, update both files simultaneously.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class LLMProviderConfig(BaseModel):
    """LLM provider configuration. Mirrors LLMProviderSchema in validation.ts."""

    provider: Literal["anthropic", "openai", "google", "ollama", "openai-compatible"]
    model: str = Field(min_length=1, max_length=200)
    api_key: str = Field(min_length=1, max_length=500)
    base_url: str | None = Field(default=None, max_length=500)


class ImageProviderConfig(BaseModel):
    """Image provider configuration. Mirrors ImageProviderSchema in validation.ts."""

    provider: Literal["dall-e-3", "replicate-flux"]
    api_key: str = Field(min_length=1, max_length=500)


class JobCreateRequest(BaseModel):
    """Request body for job creation. Mirrors JobCreateSchema in validation.ts.

    Field constraints (must stay in sync with frontend/lib/validation.ts):
      title            : min 1, max 500
      topic            : min 1, max 2000
      mode             : fiction | non_fiction
      audience         : min 1, max 500
      tone             : min 1, max 200
      target_chapters  : int, min 3, max 50, default 12
      llm              : LLMProviderConfig
      image            : ImageProviderConfig
      notification_email: optional valid email
    """

    title: str = Field(min_length=1, max_length=500)
    topic: str = Field(min_length=1, max_length=2000)
    mode: Literal["fiction", "non_fiction"]
    audience: str = Field(min_length=1, max_length=500)
    tone: str = Field(min_length=1, max_length=200)
    target_chapters: int = Field(ge=3, le=50, default=12)
    llm: LLMProviderConfig
    image: ImageProviderConfig
    notification_email: EmailStr | None = None
