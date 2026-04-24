"""Unit tests for chapter editing API."""
import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.api.deps import get_supabase


def _make_client(mock_supabase: MagicMock) -> TestClient:
    """Create a TestClient with the supabase dependency overridden."""
    app.dependency_overrides[get_supabase] = lambda: mock_supabase
    return TestClient(app)


def _mock_chapter(status: str = "generating") -> dict:
    return {
        "index": 0,
        "content": "Once upon a time...",
        "status": status,
        "qa_score": 8.5,
        "flesch_kincaid_grade": 7.2,
        "flesch_reading_ease": 65.0,
    }


def test_get_chapter_returns_content_and_scores():
    mock_supabase = MagicMock()
    mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value.data = _mock_chapter()
    client = _make_client(mock_supabase)
    resp = client.get("/jobs/job-1/chapters/0")
    assert resp.status_code == 200
    data = resp.json()
    assert data["content"] == "Once upon a time..."
    assert data["qa_score"] == 8.5
    assert data["flesch_kincaid_grade"] == 7.2


def test_get_chapter_not_found_returns_404():
    mock_supabase = MagicMock()
    mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value.data = None
    client = _make_client(mock_supabase)
    resp = client.get("/jobs/job-1/chapters/99")
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "CHAPTER_NOT_FOUND"


def test_patch_chapter_sets_status_locked():
    mock_supabase = MagicMock()
    mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value.data = {"id": "ch-1"}
    mock_supabase.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock()
    client = _make_client(mock_supabase)
    resp = client.patch("/jobs/job-1/chapters/0", json={"content": "Edited content here."})
    assert resp.status_code == 200
    assert resp.json()["status"] == "locked"


def test_patch_chapter_not_found_returns_404():
    mock_supabase = MagicMock()
    mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value.data = None
    client = _make_client(mock_supabase)
    resp = client.patch("/jobs/job-1/chapters/0", json={"content": "Some content."})
    assert resp.status_code == 404


def test_get_chapter_not_found_error_contains_job_and_index():
    """ChapterNotFoundError must embed job_id and index in message."""
    mock_supabase = MagicMock()
    mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value.data = None
    client = _make_client(mock_supabase)
    resp = client.get("/jobs/job-xyz/chapters/7")
    assert resp.status_code == 404
    body = resp.json()
    assert body["detail"]["code"] == "CHAPTER_NOT_FOUND"
    assert "7" in body["detail"]["error"]
    assert "job-xyz" in body["detail"]["error"]
