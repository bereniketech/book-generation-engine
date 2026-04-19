"""Base classes for all pipeline engines."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Literal

from pydantic import BaseModel, Field

from worker.clients.llm_client import LLMClient
from worker.memory.store import MemoryStore


class JobConfig(BaseModel):
    """Validated configuration for a book generation job."""
    job_id: str
    title: str = Field(min_length=1, max_length=500)
    topic: str = Field(min_length=1, max_length=2000)
    mode: Literal["fiction", "non_fiction"]
    audience: str = Field(min_length=1, max_length=500)
    tone: str = Field(min_length=1, max_length=200)
    target_chapters: int = Field(ge=3, le=50, default=12)
    llm_provider: str
    llm_model: str
    llm_api_key: str
    llm_base_url: str | None = None
    image_provider: str
    image_api_key: str
    notification_email: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None


class BaseEngine(ABC):
    """All pipeline engines extend this class."""
    name: str = "base"

    def __init__(self, llm: LLMClient, memory: MemoryStore, config: JobConfig) -> None:
        self.llm = llm
        self.memory = memory
        self.config = config

    @abstractmethod
    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        """Execute the engine. Receives context dict, returns updated context dict."""
        ...
