"""Unit tests for FastAPI dependency injection functions."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_supabase


# ---------------------------------------------------------------------------
# get_supabase unit tests
# ---------------------------------------------------------------------------


def test_get_supabase_returns_client_instance():
    """get_supabase delegates to get_supabase_client and returns the result."""
    mock_client = MagicMock()
    with patch("app.api.deps.get_supabase_client", return_value=mock_client) as mock_factory:
        result = get_supabase()
    mock_factory.assert_called_once()
    assert result is mock_client


def test_get_supabase_returns_singleton():
    """Repeated calls to get_supabase return the same client (singleton from lru_cache)."""
    mock_client = MagicMock()
    with patch("app.api.deps.get_supabase_client", return_value=mock_client):
        first = get_supabase()
        second = get_supabase()
    assert first is second


# ---------------------------------------------------------------------------
# Dependency override integration test
# ---------------------------------------------------------------------------


def _make_test_app() -> tuple[FastAPI, list]:
    """Build a minimal FastAPI app that exposes the injected client."""
    from fastapi import Depends
    from supabase import Client

    received: list = []
    mini_app = FastAPI()

    @mini_app.get("/probe")
    def probe(supabase: Client = Depends(get_supabase)):
        received.append(supabase)
        return {"ok": True}

    return mini_app, received


def test_dependency_override_replaces_client():
    """app.dependency_overrides[get_supabase] injects the mock — not the real client."""
    mini_app, received = _make_test_app()
    mock_client = MagicMock()
    mini_app.dependency_overrides[get_supabase] = lambda: mock_client

    client = TestClient(mini_app)
    resp = client.get("/probe")

    assert resp.status_code == 200
    assert len(received) == 1
    assert received[0] is mock_client


def test_dependency_override_isolated_per_test():
    """Overrides on one app instance do not bleed into another instance."""
    app_a, received_a = _make_test_app()
    app_b, received_b = _make_test_app()

    mock_a = MagicMock(name="mock_a")
    mock_b = MagicMock(name="mock_b")

    app_a.dependency_overrides[get_supabase] = lambda: mock_a
    app_b.dependency_overrides[get_supabase] = lambda: mock_b

    TestClient(app_a).get("/probe")
    TestClient(app_b).get("/probe")

    assert received_a[0] is mock_a
    assert received_b[0] is mock_b
    assert received_a[0] is not received_b[0]


# ---------------------------------------------------------------------------
# Route-level override: chapters
# ---------------------------------------------------------------------------


def test_chapters_route_uses_injected_supabase():
    """Chapters endpoint uses the overridden supabase — no real DB call made."""
    from app.main import app

    mock_supabase = MagicMock()
    mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value.data = []
    app.dependency_overrides[get_supabase] = lambda: mock_supabase

    tc = TestClient(app)
    resp = tc.get("/jobs/some-job/chapters")

    assert resp.status_code == 200
    assert resp.json() == {"chapters": []}
    # Confirm we hit the mock, not the real client
    mock_supabase.table.assert_called()


# ---------------------------------------------------------------------------
# Route-level override: templates
# ---------------------------------------------------------------------------


def test_templates_route_uses_injected_supabase():
    """Templates list endpoint uses the overridden supabase."""
    from app.main import app

    mock_supabase = MagicMock()
    mock_supabase.table.return_value.select.return_value.order.return_value.execute.return_value.data = []
    app.dependency_overrides[get_supabase] = lambda: mock_supabase

    tc = TestClient(app)
    resp = tc.get("/templates")

    assert resp.status_code == 200
    assert resp.json() == {"templates": []}
    mock_supabase.table.assert_called()
