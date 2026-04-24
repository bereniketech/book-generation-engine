"""Unit tests for the /v1/config/providers endpoint."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient


def _make_client():
    """Create a TestClient with mocked lifespan dependencies."""
    from app.main import app
    app.state.supabase = MagicMock()
    app.state.amqp_channel = MagicMock()
    app.state.amqp_connection = MagicMock()
    return TestClient(app, raise_server_exceptions=True)


def test_get_providers_returns_200():
    """WHEN GET /v1/config/providers is called THEN it SHALL return 200."""
    client = _make_client()
    response = client.get("/v1/config/providers")
    assert response.status_code == 200


def test_get_providers_returns_llm_providers():
    """WHEN GET /v1/config/providers is called THEN response SHALL contain llm_providers list."""
    client = _make_client()
    response = client.get("/v1/config/providers")
    body = response.json()
    assert "llm_providers" in body
    assert isinstance(body["llm_providers"], list)
    assert len(body["llm_providers"]) > 0


def test_get_providers_returns_image_providers():
    """WHEN GET /v1/config/providers is called THEN response SHALL contain image_providers list."""
    client = _make_client()
    response = client.get("/v1/config/providers")
    body = response.json()
    assert "image_providers" in body
    assert isinstance(body["image_providers"], list)
    assert len(body["image_providers"]) > 0


def test_get_providers_includes_anthropic():
    """WHEN GET /v1/config/providers is called THEN llm_providers SHALL include 'anthropic'."""
    client = _make_client()
    response = client.get("/v1/config/providers")
    body = response.json()
    assert "anthropic" in body["llm_providers"]


def test_get_providers_includes_openai():
    """WHEN GET /v1/config/providers is called THEN llm_providers SHALL include 'openai'."""
    client = _make_client()
    response = client.get("/v1/config/providers")
    body = response.json()
    assert "openai" in body["llm_providers"]


def test_get_providers_includes_dalle():
    """WHEN GET /v1/config/providers is called THEN image_providers SHALL include 'dall-e-3'."""
    client = _make_client()
    response = client.get("/v1/config/providers")
    body = response.json()
    assert "dall-e-3" in body["image_providers"]


def test_get_providers_includes_replicate():
    """WHEN GET /v1/config/providers is called THEN image_providers SHALL include 'replicate-flux'."""
    client = _make_client()
    response = client.get("/v1/config/providers")
    body = response.json()
    assert "replicate-flux" in body["image_providers"]


def test_get_providers_response_shape():
    """WHEN GET /v1/config/providers is called THEN response SHALL have exactly llm_providers and image_providers keys."""
    client = _make_client()
    response = client.get("/v1/config/providers")
    body = response.json()
    assert set(body.keys()) == {"llm_providers", "image_providers"}


def test_get_providers_llm_includes_default_model():
    """WHEN GET /v1/config/providers is called THEN each LLM provider SHALL have a default_model."""
    client = _make_client()
    response = client.get("/v1/config/providers")
    body = response.json()
    for provider, config in body["llm_providers"].items():
        assert "default_model" in config
        assert isinstance(config["default_model"], str)


def test_get_providers_anthropic_default_model():
    """WHEN GET /v1/config/providers is called THEN anthropic SHALL have claude-sonnet-4-6 as default."""
    client = _make_client()
    response = client.get("/v1/config/providers")
    body = response.json()
    assert body["llm_providers"]["anthropic"]["default_model"] == "claude-sonnet-4-6"


def test_get_providers_image_includes_default_model():
    """WHEN GET /v1/config/providers is called THEN each image provider SHALL have a default_model."""
    client = _make_client()
    response = client.get("/v1/config/providers")
    body = response.json()
    for provider, config in body["image_providers"].items():
        assert "default_model" in config
        assert isinstance(config["default_model"], str)


def test_get_providers_expected_llm_list():
    """WHEN GET /v1/config/providers is called THEN llm_providers SHALL match the canonical list."""
    client = _make_client()
    response = client.get("/v1/config/providers")
    body = response.json()
    expected = {"anthropic", "openai", "google", "ollama", "openai-compatible"}
    assert set(body["llm_providers"]) == expected


def test_get_providers_expected_image_list():
    """WHEN GET /v1/config/providers is called THEN image_providers SHALL match the canonical list."""
    client = _make_client()
    response = client.get("/v1/config/providers")
    body = response.json()
    expected = {"dall-e-3", "replicate-flux"}
    assert set(body["image_providers"]) == expected
