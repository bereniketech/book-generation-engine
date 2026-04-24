"""Unit tests for cover approval API."""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi.testclient import TestClient

from app.main import app
from app.api.deps import get_supabase


def _make_client(mock_supabase: MagicMock) -> TestClient:
    """Create a TestClient with the supabase dependency overridden."""
    app.dependency_overrides[get_supabase] = lambda: mock_supabase
    return TestClient(app)


def _mock_job(cover_status: str | None = "awaiting_approval") -> dict:
    return {
        "id": "job-1",
        "status": "awaiting_cover_approval",
        "cover_status": cover_status,
        "cover_url": "https://storage.example.com/covers/job-1.png",
        "config": {},
    }


def test_get_cover_returns_url_and_status():
    mock_supabase = MagicMock()
    mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = _mock_job()
    client = _make_client(mock_supabase)
    resp = client.get("/jobs/job-1/cover")
    assert resp.status_code == 200
    assert resp.json()["cover_url"] == "https://storage.example.com/covers/job-1.png"
    assert resp.json()["cover_status"] == "awaiting_approval"


def test_approve_cover_sets_assembling():
    mock_supabase = MagicMock()
    mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = _mock_job("awaiting_approval")
    mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()
    client = _make_client(mock_supabase)
    resp = client.post("/jobs/job-1/cover/approve")
    assert resp.status_code == 200
    assert resp.json()["status"] == "assembling"


def test_approve_cover_no_pending_returns_409():
    mock_supabase = MagicMock()
    mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = _mock_job("approved")
    client = _make_client(mock_supabase)
    resp = client.post("/jobs/job-1/cover/approve")
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "INVALID_STATE_TRANSITION"


def test_revise_cover_sets_revising():
    mock_supabase = MagicMock()
    mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = _mock_job("awaiting_approval")
    mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

    # Mock the cover_revision_service.add_revision call
    with patch("app.api.cover.cover_revision_service.add_revision", new_callable=AsyncMock) as mock_add_revision:
        mock_add_revision.return_value = {
            "id": "rev-1",
            "job_id": "job-1",
            "feedback": "Make it darker",
            "revision_number": 1,
            "requested_at": "2026-04-24T12:00:00Z",
        }
        client = _make_client(mock_supabase)
        resp = client.post("/jobs/job-1/cover/revise", json={"feedback": "Make it darker"})
        assert resp.status_code == 200
        assert resp.json()["cover_status"] == "revising"
        # Verify the service was called
        mock_add_revision.assert_called_once_with(mock_supabase, "job-1", "Make it darker")


def test_get_cover_job_not_found_returns_structured_error():
    mock_supabase = MagicMock()
    mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = None
    client = _make_client(mock_supabase)
    resp = client.get("/jobs/missing-job/cover")
    assert resp.status_code == 404
    body = resp.json()
    assert body["detail"]["code"] == "JOB_NOT_FOUND"
    assert "missing-job" in body["detail"]["error"]


def test_revise_cover_no_pending_returns_structured_error():
    mock_supabase = MagicMock()
    mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = _mock_job("approved")

    # Mock the cover_revision_service.add_revision call (should not be called due to validation failure)
    with patch("app.api.cover.cover_revision_service.add_revision", new_callable=AsyncMock) as mock_add_revision:
        client = _make_client(mock_supabase)
        resp = client.post("/jobs/job-1/cover/revise", json={"feedback": "Redo it"})
        assert resp.status_code == 409
        body = resp.json()
        assert body["detail"]["code"] == "INVALID_STATE_TRANSITION"
        assert isinstance(body["detail"]["error"], str)
        # Service should not have been called because validation failed
        mock_add_revision.assert_not_called()
