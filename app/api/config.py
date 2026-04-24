"""Configuration endpoints (read-only)."""
from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/v1/config", tags=["config"])

_LLM_PROVIDERS = {
    "anthropic": {"models": ["claude-opus", "claude-sonnet-4-6", "claude-haiku"], "default_model": "claude-sonnet-4-6"},
    "openai": {"models": ["gpt-4-turbo", "gpt-4", "gpt-3.5-turbo"], "default_model": "gpt-4-turbo"},
    "google": {"models": ["gemini-pro", "gemini-1.5-pro"], "default_model": "gemini-1.5-pro"},
    "ollama": {"models": [], "default_model": ""},
    "openai-compatible": {"models": [], "default_model": ""},
}
_IMAGE_PROVIDERS = {
    "dall-e-3": {"default_model": "dall-e-3"},
    "replicate-flux": {"default_model": "flux"},
}


@router.get("/providers")
async def get_providers() -> dict:
    """Get list of supported LLM and image providers with defaults.

    Frontend calls this on app load to populate provider dropdowns and initialize defaults.
    This is the single source of truth for available providers and their defaults — updating
    this dict is sufficient for provider additions or default changes; no frontend changes required.
    """
    return {
        "llm_providers": _LLM_PROVIDERS,
        "image_providers": _IMAGE_PROVIDERS,
    }
