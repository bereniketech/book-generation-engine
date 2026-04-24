"""Unit tests for job config template endpoints."""
import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.api.deps import get_supabase


def _make_client(mock_supabase: MagicMock) -> TestClient:
    """Create a TestClient with the supabase dependency overridden."""
    app.dependency_overrides[get_supabase] = lambda: mock_supabase
    return TestClient(app)


def test_list_templates_returns_list():
    mock_supabase = MagicMock()
    mock_supabase.table.return_value.select.return_value.order.return_value.execute.return_value.data = [
        {"id": "t-1", "name": "fiction-default", "config": {"genre": "fiction"}, "created_at": "2024-01-01"}
    ]
    client = _make_client(mock_supabase)
    resp = client.get("/templates")
    assert resp.status_code == 200
    assert resp.json()["templates"][0]["name"] == "fiction-default"


def test_create_template_returns_201():
    mock_supabase = MagicMock()
    mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [
        {"id": "t-new", "name": "new-template", "config": {"genre": "sci-fi"}}
    ]
    client = _make_client(mock_supabase)
    resp = client.post("/templates", json={"name": "new-template", "config": {"genre": "sci-fi"}})
    assert resp.status_code == 201
    assert resp.json()["id"] == "t-new"


def test_create_template_duplicate_name_returns_409():
    mock_supabase = MagicMock()
    mock_supabase.table.return_value.insert.return_value.execute.side_effect = Exception("duplicate key unique constraint")
    client = _make_client(mock_supabase)
    resp = client.post("/templates", json={"name": "existing", "config": {}})
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "TEMPLATE_EXISTS"


def test_create_template_internal_error_returns_structured_error():
    mock_supabase = MagicMock()
    mock_supabase.table.return_value.insert.return_value.execute.side_effect = Exception("connection reset")
    client = _make_client(mock_supabase)
    resp = client.post("/templates", json={"name": "broken", "config": {}})
    assert resp.status_code == 500
    body = resp.json()
    assert body["detail"]["code"] == "INTERNAL_ERROR"
    assert isinstance(body["detail"]["error"], str)


def test_create_job_with_template_merges_config():
    mock_supabase = MagicMock()
    mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {
        "config": {"genre": "fiction", "chapters": 12, "language": "en"}
    }
    mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [{"id": "new-job"}]

    client = _make_client(mock_supabase)
    resp = client.post("/jobs", json={
        "config": {"genre": "sci-fi", "title": "Override Title"},
        "template_id": "t-1",
    })

    assert resp.status_code == 201
    insert_call = mock_supabase.table.return_value.insert.call_args[0][0]
    assert insert_call["config"]["genre"] == "sci-fi"
    assert insert_call["config"]["chapters"] == 12
    assert insert_call["config"]["title"] == "Override Title"
