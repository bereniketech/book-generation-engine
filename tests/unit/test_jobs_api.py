"""Unit tests for job management REST API endpoints."""
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.api.deps import get_supabase


def _mock_job(status: str = "generating") -> dict:
    return {
        "id": "job-1",
        "status": status,
        "config": {},
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
        "notification_email": None,
    }


def _make_client(mock_supabase: MagicMock) -> TestClient:
    """Create a TestClient with the supabase dependency overridden."""
    app.dependency_overrides[get_supabase] = lambda: mock_supabase
    # amqp_channel stub still needed for create_job (uses request.app.state)
    app.state.amqp_channel = MagicMock()
    app.state.amqp_connection = MagicMock()
    return TestClient(app, raise_server_exceptions=True)


def _mock_supabase(job_data=None, insert_data=None) -> MagicMock:
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
    mock_sb = _mock_supabase(job_data=_mock_job("generating"))
    client = _make_client(mock_sb)
    resp = client.patch("/v1/jobs/job-1/pause")
    assert resp.status_code == 200
    assert resp.json()["status"] == "paused"


def test_pause_job_on_complete_returns_409():
    mock_sb = _mock_supabase(job_data=_mock_job("complete"))
    client = _make_client(mock_sb)
    resp = client.patch("/v1/jobs/job-1/pause")
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "INVALID_STATE_TRANSITION"


def test_pause_job_on_cancelled_returns_409():
    mock_sb = _mock_supabase(job_data=_mock_job("cancelled"))
    client = _make_client(mock_sb)
    resp = client.patch("/v1/jobs/job-1/pause")
    assert resp.status_code == 409


# ---------------------------------------------------------------------------
# resume
# ---------------------------------------------------------------------------


def test_resume_job_returns_200():
    mock_sb = _mock_supabase(job_data=_mock_job("paused"))
    client = _make_client(mock_sb)
    resp = client.patch("/v1/jobs/job-1/resume")
    assert resp.status_code == 200
    assert resp.json()["status"] == "queued"


# ---------------------------------------------------------------------------
# cancel / delete
# ---------------------------------------------------------------------------


def test_cancel_job_returns_204():
    mock_sb = _mock_supabase(job_data=_mock_job("generating"))
    client = _make_client(mock_sb)
    resp = client.delete("/v1/jobs/job-1")
    assert resp.status_code == 204


# ---------------------------------------------------------------------------
# 404 behaviour
# ---------------------------------------------------------------------------


def test_get_job_not_found_returns_404():
    mock_sb = _mock_supabase(job_data=None)
    client = _make_client(mock_sb)
    resp = client.patch("/v1/jobs/bad-id/pause")
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "JOB_NOT_FOUND"


# ---------------------------------------------------------------------------
# restart
# ---------------------------------------------------------------------------


def test_restart_job_returns_201_with_new_job_id():
    mock_sb = _mock_supabase(
        job_data=_mock_job("failed"),
        insert_data=[{"id": "new-job-id"}],
    )
    client = _make_client(mock_sb)
    resp = client.post("/v1/jobs/job-1/restart")
    assert resp.status_code == 201
    assert resp.json()["new_job_id"] == "new-job-id"


# ---------------------------------------------------------------------------
# get_job structured error
# ---------------------------------------------------------------------------


def test_get_job_not_found_returns_structured_error():
    """get_job must return {error, code} not a plain string."""
    mock_sb = MagicMock()
    client = _make_client(mock_sb)
    with patch("app.api.jobs.job_service.get_job", return_value=None):
        resp = client.get("/v1/jobs/missing-id")
    assert resp.status_code == 404
    body = resp.json()
    assert body["detail"]["code"] == "JOB_NOT_FOUND"
    assert isinstance(body["detail"]["error"], str)
    assert "missing-id" in body["detail"]["error"]


def test_pause_job_structured_error_has_valid_transitions():
    """State transition 409 must include valid_transitions field."""
    mock_sb = _mock_supabase(job_data=_mock_job("complete"))
    client = _make_client(mock_sb)
    resp = client.patch("/v1/jobs/job-1/pause")
    assert resp.status_code == 409
    body = resp.json()
    assert body["detail"]["code"] == "INVALID_STATE_TRANSITION"
    assert "valid_transitions" in body["detail"]
    assert isinstance(body["detail"]["valid_transitions"], list)


# ---------------------------------------------------------------------------
# list jobs
# ---------------------------------------------------------------------------


def test_list_jobs_returns_jobs_dict():
    mock_sb = MagicMock()
    jobs = [_mock_job("generating"), _mock_job("complete")]
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
    client = _make_client(mock_sb)
    resp = client.get("/v1/jobs")
    assert resp.status_code == 200
    body = resp.json()
    assert "jobs" in body
    assert "total" in body
    assert body["page"] == 1
    assert body["limit"] == 20


def test_list_jobs_with_status_filter():
    mock_sb = MagicMock()
    list_result = MagicMock()
    list_result.data = [_mock_job("generating")]
    list_result.count = 1
    (
        mock_sb.table.return_value
        .select.return_value
        .eq.return_value
        .order.return_value
        .range.return_value
        .execute.return_value
    ) = list_result
    client = _make_client(mock_sb)
    resp = client.get("/v1/jobs?status=generating")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
