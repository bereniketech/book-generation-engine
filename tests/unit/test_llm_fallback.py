"""Unit tests for LLM provider fallback chain."""
import pytest
from unittest.mock import AsyncMock, patch

from worker.clients.llm_client import call_llm_with_fallback


@pytest.mark.asyncio
async def test_primary_provider_success_no_fallback():
    with patch("worker.clients.llm_client._call_provider", new_callable=AsyncMock) as mock_call:
        mock_call.return_value = "Generated text."
        result = await call_llm_with_fallback("Test prompt", "job-1", "planning")
    assert result == "Generated text."
    assert mock_call.call_count == 1
    assert mock_call.call_args[1]["provider"] == "anthropic"


@pytest.mark.asyncio
async def test_primary_fails_falls_back_to_openai():
    call_count = 0
    async def mock_provider(provider, prompt, temperature, max_tokens):
        nonlocal call_count
        call_count += 1
        if provider == "anthropic":
            raise ConnectionError("Anthropic 503")
        return "OpenAI response."

    with patch("worker.clients.llm_client._call_provider", side_effect=mock_provider):
        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await call_llm_with_fallback("prompt", "job-1", "planning")
    assert result == "OpenAI response."


@pytest.mark.asyncio
async def test_all_providers_fail_raises_runtime_error():
    async def always_fail(provider, prompt, temperature, max_tokens):
        raise ConnectionError(f"{provider} failed")

    with patch("worker.clients.llm_client._call_provider", side_effect=always_fail):
        with patch("asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(RuntimeError, match="All LLM providers failed"):
                await call_llm_with_fallback("prompt", "job-1", "planning")


@pytest.mark.asyncio
async def test_retry_with_backoff_before_fallback():
    attempts = []
    async def track_calls(provider, prompt, temperature, max_tokens):
        attempts.append(provider)
        if provider == "anthropic":
            raise ConnectionError("fail")
        return "ok"

    with patch("worker.clients.llm_client._call_provider", side_effect=track_calls):
        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await call_llm_with_fallback("prompt", "job-1", "planning")

    assert attempts.count("anthropic") == 2  # MAX_LLM_RETRIES default is 2
    assert result == "ok"
