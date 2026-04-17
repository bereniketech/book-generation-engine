"""Unit tests for LLMClient. All provider SDK calls are mocked."""
from unittest.mock import MagicMock, patch

import pytest

from worker.clients.exceptions import ProviderRateLimitError, UnsupportedProviderError
from worker.clients.llm_client import LLMClient


def test_unsupported_provider_raises_at_construction():
    with pytest.raises(UnsupportedProviderError, match="badprovider"):
        LLMClient(provider="badprovider", model="x", api_key="k")  # type: ignore[arg-type]


def test_supported_providers_construct_without_error():
    with patch("worker.clients.llm_client.anthropic.Anthropic"):
        LLMClient(provider="anthropic", model="claude-sonnet-4-6", api_key="test-key")

    with patch("worker.clients.llm_client.openai.OpenAI"):
        LLMClient(provider="openai", model="gpt-4o", api_key="test-key")
        LLMClient(provider="openai-compatible", model="some-model", api_key="k", base_url="http://x")
        LLMClient(provider="ollama", model="llama3", api_key="k")

    with patch("worker.clients.llm_client.genai.configure"), \
         patch("worker.clients.llm_client.genai.GenerativeModel"):
        LLMClient(provider="google", model="gemini-pro", api_key="k")


def test_anthropic_complete_returns_text():
    mock_client = MagicMock()
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text="Generated text")]
    )
    with patch("worker.clients.llm_client.anthropic.Anthropic", return_value=mock_client):
        llm = LLMClient(provider="anthropic", model="claude-sonnet-4-6", api_key="k")
    result = llm.complete("Hello", "You are helpful")
    assert result == "Generated text"
    mock_client.messages.create.assert_called_once()


def test_openai_complete_returns_text():
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content="OpenAI response"))]
    )
    with patch("worker.clients.llm_client.openai.OpenAI", return_value=mock_client):
        llm = LLMClient(provider="openai", model="gpt-4o", api_key="k")
    result = llm.complete("Hello")
    assert result == "OpenAI response"


def test_google_complete_returns_text():
    mock_model = MagicMock()
    mock_model.generate_content.return_value = MagicMock(text="Gemini response")
    with patch("worker.clients.llm_client.genai.configure"), \
         patch("worker.clients.llm_client.genai.GenerativeModel", return_value=mock_model):
        llm = LLMClient(provider="google", model="gemini-pro", api_key="k")
    result = llm.complete("Hello", "System")
    assert result == "Gemini response"
    mock_model.generate_content.assert_called_with("System\n\nHello")


def test_ollama_uses_local_base_url_by_default():
    with patch("worker.clients.llm_client.openai.OpenAI") as MockOpenAI:
        LLMClient(provider="ollama", model="llama3", api_key="k")
    call_kwargs = MockOpenAI.call_args[1]
    assert "localhost:11434" in call_kwargs["base_url"]


def test_rate_limit_retries_then_raises():
    import openai as _openai

    mock_client = MagicMock()
    mock_client.messages.create.side_effect = _openai.RateLimitError(
        "rate limited", response=MagicMock(status_code=429), body={}
    )
    with patch("worker.clients.llm_client.anthropic.Anthropic", return_value=mock_client), \
         patch("worker.clients.llm_client.time.sleep"):
        llm = LLMClient(provider="anthropic", model="claude-sonnet-4-6", api_key="k")
        with pytest.raises(ProviderRateLimitError):
            llm.complete("test")

    assert mock_client.messages.create.call_count == 3  # MAX_RETRIES
