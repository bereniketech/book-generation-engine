"""Unit tests for job management REST API endpoints."""
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient


def _mock_job(status: str = "generating") -> dict:
    return {
        "id": "job-1",
        "status": status,
        "config": {},
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
        "notification_email": None,
    }


def _make_client():
    """Create a TestClient with mocked lifespan dependencies."""
    from app.main import app

    # Provide stub state so lifespan is not required
    app.state.supabase = MagicMock()
    app.state.amqp_channel = MagicMock()
    app.state.amqp_connection = MagicMock()
    return TestClient(app, raise_server_exceptions=True)


def _mock_supabase(job_data=None, insert_data=None):
    """Build a MagicMock supabase client with configurable responses."""
    mock = MagicMock()
    # select().eq().single().execute().data
    mock.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = job_data
    # update().eq().execute()
    mock.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()
    # insert().execute()
    if insert_data is not None:
        mock.table.return_value.insert.return_value.execute.return_value.data = insert_data
    return mock


# ---------------------------------------------------------------------------
# pause
# ---------------------------------------------------------------------------


def test_pause_job_returns_200():
    client = _make_client()
    mock_sb = _mock_supabase(job_data=_mock_job("generating"))
    client.app.state.supabase = mock_sb
    resp = client.patch("/v1/jobs/job-1/pause")
    assert resp.status_code == 200
    assert resp.json()["status"] == "paused"


def test_pause_job_on_complete_returns_409():
    client = _make_client()
    mock_sb = _mock_supabase(job_data=_mock_job("complete"))
    client.app.state.supabase = mock_sb
    resp = client.patch("/v1/jobs/job-1/pause")
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "INVALID_STATE_TRANSITION"


def test_pause_job_on_cancelled_returns_409():
    client = _make_client()
    mock_sb = _mock_supabase(job_data=_mock_job("cancelled"))
    client.app.state.supabase = mock_sb
    resp = client.patch("/v1/jobs/job-1/pause")
    assert resp.status_code == 409


# ---------------------------------------------------------------------------
# resume
# ---------------------------------------------------------------------------


def test_resume_job_returns_200():
    client = _make_client()
    mock_sb = _mock_supabase(job_data=_mock_job("paused"))
    client.app.state.supabase = mock_sb
    resp = client.patch("/v1/jobs/job-1/resume")
    assert resp.status_code == 200
    assert resp.json()["status"] == "queued"


# ---------------------------------------------------------------------------
# cancel / delete
# ---------------------------------------------------------------------------


def test_cancel_job_returns_204():
    client = _make_client()
    mock_sb = _mock_supabase(job_data=_mock_job("generating"))
    client.app.state.supabase = mock_sb
    resp = client.delete("/v1/jobs/job-1")
    assert resp.status_code == 204


# ---------------------------------------------------------------------------
# 404 behaviour
# ---------------------------------------------------------------------------


def test_get_job_not_found_returns_404():
    client = _make_client()
    mock_sb = _mock_supabase(job_data=None)
    client.app.state.supabase = mock_sb
    resp = client.patch("/v1/jobs/bad-id/pause")
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "JOB_NOT_FOUND"


# ---------------------------------------------------------------------------
# restart
# ---------------------------------------------------------------------------


def test_restart_job_returns_201_with_new_job_id():
    client = _make_client()
    mock_sb = _mock_supabase(
        job_data=_mock_job("failed"),
        insert_data=[{"id": "new-job-id"}],
    )
    client.app.state.supabase = mock_sb
    resp = client.post("/v1/jobs/job-1/restart")
    assert resp.status_code == 201
    assert resp.json()["new_job_id"] == "new-job-id"


# ---------------------------------------------------------------------------
# list jobs
# ---------------------------------------------------------------------------


def test_list_jobs_returns_jobs_dict():
    client = _make_client()
    mock_sb = MagicMock()
    jobs = [_mock_job("generating"), _mock_job("complete")]
    # Chain for list: select().eq().order().range().execute()
    list_result = MagicMock()
    list_result.data = jobs
    list_result.count = 2
    (
        mock_sb.table.return_value
        .select.return_value
        .order.return_value
        .range.return_value
        .execute.return_value
    ) = list_result
    client.app.state.supabase = mock_sb
    resp = client.get("/v1/jobs")
    assert resp.status_code == 200
    body = resp.json()
    assert "jobs" in body
    assert "total" in body
    assert body["page"] == 1
    assert body["limit"] == 20


def test_list_jobs_with_status_filter():
    client = _make_client()
    mock_sb = MagicMock()
    list_result = MagicMock()
    list_result.data = [_mock_job("generating")]
    list_result.count = 1
    # When status filter is applied, the chain includes an extra .eq() call
    (
        mock_sb.table.return_value
        .select.return_value
        .eq.return_value
        .order.return_value
        .range.return_value
        .execute.return_value
    ) = list_result
    client.app.state.supabase = mock_sb
    resp = client.get("/v1/jobs?status=generating")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
