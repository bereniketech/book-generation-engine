"""Unit tests for cover approval API."""
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _mock_job(cover_status: str | None = "awaiting_approval") -> dict:
    return {
        "id": "job-1",
        "status": "awaiting_cover_approval",
        "cover_status": cover_status,
        "cover_url": "https://storage.example.com/covers/job-1.png",
        "config": {},
    }


def test_get_cover_returns_url_and_status():
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = _mock_job()
    with patch("app.api.cover.get_supabase_client", return_value=mock_client):
        resp = client.get("/jobs/job-1/cover")
    assert resp.status_code == 200
    assert resp.json()["cover_url"] == "https://storage.example.com/covers/job-1.png"
    assert resp.json()["cover_status"] == "awaiting_approval"


def test_approve_cover_sets_assembling():
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = _mock_job("awaiting_approval")
    mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()
    with patch("app.api.cover.get_supabase_client", return_value=mock_client):
        resp = client.post("/jobs/job-1/cover/approve")
    assert resp.status_code == 200
    assert resp.json()["status"] == "assembling"


def test_approve_cover_no_pending_returns_409():
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = _mock_job("approved")
    with patch("app.api.cover.get_supabase_client", return_value=mock_client):
        resp = client.post("/jobs/job-1/cover/approve")
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "INVALID_STATE_TRANSITION"


def test_revise_cover_sets_revising():
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = _mock_job("awaiting_approval")
    mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()
    with patch("app.api.cover.get_supabase_client", return_value=mock_client):
        resp = client.post("/jobs/job-1/cover/revise", json={"feedback": "Make it darker"})
    assert resp.status_code == 200
    assert resp.json()["cover_status"] == "revising"


def test_get_cover_job_not_found_returns_structured_error():
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = None
    with patch("app.api.cover.get_supabase_client", return_value=mock_client):
        resp = client.get("/jobs/missing-job/cover")
    assert resp.status_code == 404
    body = resp.json()
    assert body["detail"]["code"] == "JOB_NOT_FOUND"
    assert "missing-job" in body["detail"]["error"]


def test_revise_cover_no_pending_returns_structured_error():
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = _mock_job("approved")
    with patch("app.api.cover.get_supabase_client", return_value=mock_client):
        resp = client.post("/jobs/job-1/cover/revise", json={"feedback": "Redo it"})
    assert resp.status_code == 409
    body = resp.json()
    assert body["detail"]["code"] == "INVALID_STATE_TRANSITION"
    assert isinstance(body["detail"]["error"], str)
