"""Unit tests for per-job LLM hyperparameter controls."""
import sys
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def _make_google_mock() -> MagicMock:
    """Return a minimal google.generativeai mock to prevent PyO3 re-init on import."""
    mock_genai = MagicMock()
    mock_google = MagicMock()
    mock_google.generativeai = mock_genai
    return mock_genai


@pytest.mark.asyncio
async def test_call_anthropic_passes_temperature_when_set():
    mock_anthropic = MagicMock()
    mock_client_instance = AsyncMock()
    mock_anthropic.AsyncAnthropic.return_value = mock_client_instance
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="Response")]
    mock_client_instance.messages.create.return_value = mock_response

    mock_genai = _make_google_mock()
    extra = {
        "google.generativeai": mock_genai,
        "google": MagicMock(generativeai=mock_genai),
    }
    with patch.dict("sys.modules", {"anthropic": mock_anthropic, **extra}):
        # Remove cached module so local import inside _call_anthropic uses our mock
        sys.modules.pop("worker.clients.llm_client", None)
        from worker.clients.llm_client import _call_anthropic
        await _call_anthropic("Test prompt", temperature=0.9, max_tokens=512)

    create_kwargs = mock_client_instance.messages.create.call_args[1]
    assert create_kwargs["temperature"] == 0.9
    assert create_kwargs["max_tokens"] == 512


@pytest.mark.asyncio
async def test_call_anthropic_omits_temperature_when_none():
    mock_anthropic = MagicMock()
    mock_client_instance = AsyncMock()
    mock_anthropic.AsyncAnthropic.return_value = mock_client_instance
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="Response")]
    mock_client_instance.messages.create.return_value = mock_response

    mock_genai = _make_google_mock()
    extra = {
        "google.generativeai": mock_genai,
        "google": MagicMock(generativeai=mock_genai),
    }
    with patch.dict("sys.modules", {"anthropic": mock_anthropic, **extra}):
        sys.modules.pop("worker.clients.llm_client", None)
        from worker.clients.llm_client import _call_anthropic
        await _call_anthropic("Test prompt", temperature=None, max_tokens=None)

    create_kwargs = mock_client_instance.messages.create.call_args[1]
    assert "temperature" not in create_kwargs


@pytest.mark.asyncio
async def test_call_llm_with_fallback_passes_hyperparams():
    from worker.clients.llm_client import call_llm_with_fallback

    async def mock_provider(provider, prompt, temperature, max_tokens):
        assert temperature == 0.7
        assert max_tokens == 1024
        return "OK"

    with patch("worker.clients.llm_client._call_provider", side_effect=mock_provider):
        result = await call_llm_with_fallback(
            "prompt", "job-1", "planning", temperature=0.7, max_tokens=1024
        )

    assert result == "OK"
