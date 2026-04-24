"""Integration tests for jobs API endpoints."""
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.jobs import router as jobs_router
from app.api.deps import get_supabase


@asynccontextmanager
async def _mock_lifespan(app: FastAPI):
    """Lifespan that injects mock state without real connections."""
    app.state.supabase = MagicMock()
    app.state.amqp_channel = MagicMock()
    app.state.amqp_connection = MagicMock()
    yield


_test_app = FastAPI(lifespan=_mock_lifespan)
_test_app.include_router(jobs_router)
# Override the Supabase dependency so no real credentials are needed in tests
_mock_supabase = MagicMock()
_test_app.dependency_overrides[get_supabase] = lambda: _mock_supabase


@pytest.fixture()
def client():
    with TestClient(_test_app) as c:
        yield c


def make_job_body() -> dict:
    return {
        "title": "Test Book",
        "topic": "Testing concepts",
        "mode": "fiction",
        "audience": "Developers",
        "tone": "Casual",
        "target_chapters": 3,
        "llm": {"provider": "anthropic", "model": "claude-sonnet-4-6", "api_key": "test-key"},
        "image": {"provider": "dall-e-3", "api_key": "img-key"},
        "notification_email": "test@example.com",
    }


def test_create_job_returns_201_with_job_id(client):
    with patch("app.services.job_creation_service.job_service.create_job") as mock_create, \
         patch("app.services.job_creation_service.publish_job", new_callable=AsyncMock):
        mock_create.return_value = {"id": "job-uuid-1"}
        client.app.state.amqp_channel = MagicMock()

        response = client.post("/v1/jobs", json=make_job_body())

    assert response.status_code == 201
    data = response.json()
    assert "job_id" in data
    assert "ws_url" in data


def test_get_job_returns_404_for_unknown_id(client):
    with patch("app.api.jobs.job_service.get_job", return_value=None):
        response = client.get("/v1/jobs/nonexistent-id")
    assert response.status_code == 404
    body = response.json()
    # Structured error envelope: detail contains {"error": ..., "code": ...}
    assert "detail" in body
    assert body["detail"]["code"] == "JOB_NOT_FOUND"


def test_get_job_redacts_api_keys(client):
    with patch("app.api.jobs.job_service.get_job", return_value={
        "id": "job-1",
        "status": "queued",
        "config": {"llm": {"api_key": "***REDACTED***"}, "image": {"api_key": "***REDACTED***"}},
    }):
        response = client.get("/v1/jobs/job-1")
    assert response.status_code == 200
    config = response.json()["config"]
    assert config["llm"]["api_key"] == "***REDACTED***"
