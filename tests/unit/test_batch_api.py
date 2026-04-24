"""Unit tests for batch job submission."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.api.deps import get_supabase


def _make_client(mock_supabase: MagicMock) -> TestClient:
    """Create a TestClient with the supabase dependency overridden."""
    app.dependency_overrides[get_supabase] = lambda: mock_supabase
    return TestClient(app)


def test_batch_submit_json_valid_jobs():
    mock_supabase = MagicMock()
    mock_supabase.table.return_value.select.return_value.in_.return_value.execute.return_value.count = 0
    # Mock the insert response for job creation
    mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [{"id": "job-abc"}]
    # Mock the update response for batch_id
    mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = None

    mock_connection = AsyncMock()
    mock_channel = AsyncMock()
    mock_connection.channel.return_value = mock_channel

    client = _make_client(mock_supabase)
    with patch("aio_pika.connect_robust", return_value=mock_connection), \
         patch("app.api.batch.create_job_service", new_callable=AsyncMock) as mock_create_job:

        # Mock the create_job_service to return valid results
        from app.services.job_creation_service import JobCreateResult
        mock_create_job.return_value = JobCreateResult(
            job_id="job-1",
            ws_url="/v1/ws/job-1",
        )

        resp = client.post("/batch", json={
            "format": "json",
            "jobs": [
                {
                    "title": "Book One",
                    "topic": "Test topic",
                    "mode": "fiction",
                    "audience": "General",
                    "tone": "Casual",
                    "target_chapters": 10,
                    "llm": {"provider": "anthropic", "model": "claude-sonnet-4-6", "api_key": "key1"},
                    "image": {"provider": "dall-e-3", "api_key": "img-key1"},
                },
                {
                    "title": "Book Two",
                    "topic": "Another topic",
                    "mode": "non_fiction",
                    "audience": "Experts",
                    "tone": "Formal",
                    "target_chapters": 8,
                    "llm": {"provider": "openai", "model": "gpt-4", "api_key": "key2"},
                    "image": {"provider": "replicate-flux", "api_key": "img-key2"},
                }
            ]
        })

    assert resp.status_code == 200
    data = resp.json()
    assert data["enqueued"] == 2
    assert data["skipped"] == 0
    assert len(data["job_ids"]) == 2


def test_batch_submit_invalid_row_skipped():
    mock_supabase = MagicMock()
    mock_supabase.table.return_value.select.return_value.in_.return_value.execute.return_value.count = 0
    mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [{"id": "job-abc"}]
    mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = None

    mock_connection = AsyncMock()
    mock_channel = AsyncMock()
    mock_connection.channel.return_value = mock_channel

    client = _make_client(mock_supabase)
    with patch("aio_pika.connect_robust", return_value=mock_connection), \
         patch("app.api.batch.create_job_service", new_callable=AsyncMock) as mock_create_job:

        from app.services.job_creation_service import JobCreateResult
        mock_create_job.return_value = JobCreateResult(
            job_id="job-1",
            ws_url="/v1/ws/job-1",
        )

        resp = client.post("/batch", json={
            "format": "json",
            "jobs": [
                {
                    "title": "Valid Book",
                    "topic": "Test topic",
                    "mode": "fiction",
                    "audience": "General",
                    "tone": "Casual",
                    "target_chapters": 10,
                    "llm": {"provider": "anthropic", "model": "claude-sonnet-4-6", "api_key": "key1"},
                    "image": {"provider": "dall-e-3", "api_key": "img-key1"},
                },
                {"bad_field": "no title or genre"}
            ]
        })

    assert resp.status_code == 200
    data = resp.json()
    assert data["enqueued"] == 1
    assert data["skipped"] == 1
    assert len(data["errors"]) == 1
    assert data["errors"][0]["row"] == 1
    assert "errors" in data["errors"][0]


def test_batch_all_invalid_returns_422():
    mock_supabase = MagicMock()
    mock_supabase.table.return_value.select.return_value.in_.return_value.execute.return_value.count = 0

    mock_connection = AsyncMock()
    mock_channel = AsyncMock()
    mock_connection.channel.return_value = mock_channel

    client = _make_client(mock_supabase)
    with patch("aio_pika.connect_robust", return_value=mock_connection):
        resp = client.post("/batch", json={
            "format": "json",
            "jobs": [{"bad": "no title"}, {"also_bad": "missing"}]
        })

    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "EMPTY_BATCH"
