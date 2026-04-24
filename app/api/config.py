"""Configuration endpoints (read-only)."""
from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/v1/config", tags=["config"])

_LLM_PROVIDERS = ["anthropic", "openai", "google", "ollama", "openai-compatible"]
_IMAGE_PROVIDERS = ["dall-e-3", "replicate-flux"]


@router.get("/providers")
async def get_providers() -> dict:
    """Get list of supported LLM and image providers.

    Frontend calls this on app load to populate provider dropdowns.
    This is the single source of truth for available providers — updating
    this list is sufficient for provider additions; no frontend changes required.
    """
    return {
        "llm_providers": _LLM_PROVIDERS,
        "image_providers": _IMAGE_PROVIDERS,
    }
