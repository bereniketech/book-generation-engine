"""Unit tests for job config template endpoints."""
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_list_templates_returns_list():
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.order.return_value.execute.return_value.data = [
        {"id": "t-1", "name": "fiction-default", "config": {"genre": "fiction"}, "created_at": "2024-01-01"}
    ]
    with patch("app.api.templates._client", return_value=mock_client):
        resp = client.get("/templates")
    assert resp.status_code == 200
    assert resp.json()["templates"][0]["name"] == "fiction-default"


def test_create_template_returns_201():
    mock_client = MagicMock()
    mock_client.table.return_value.insert.return_value.execute.return_value.data = [
        {"id": "t-new", "name": "new-template", "config": {"genre": "sci-fi"}}
    ]
    with patch("app.api.templates._client", return_value=mock_client):
        resp = client.post("/templates", json={"name": "new-template", "config": {"genre": "sci-fi"}})
    assert resp.status_code == 201
    assert resp.json()["id"] == "t-new"


def test_create_template_duplicate_name_returns_409():
    mock_client = MagicMock()
    mock_client.table.return_value.insert.return_value.execute.side_effect = Exception("duplicate key unique constraint")
    with patch("app.api.templates._client", return_value=mock_client):
        resp = client.post("/templates", json={"name": "existing", "config": {}})
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "TEMPLATE_EXISTS"


def test_create_job_with_template_merges_config():
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {
        "config": {"genre": "fiction", "chapters": 12, "language": "en"}
    }
    mock_client.table.return_value.insert.return_value.execute.return_value.data = [{"id": "new-job"}]

    with patch("app.api.jobs._client", return_value=mock_client):
        resp = client.post("/jobs", json={
            "config": {"genre": "sci-fi", "title": "Override Title"},
            "template_id": "t-1",
        })

    assert resp.status_code == 201
    insert_call = mock_client.table.return_value.insert.call_args[0][0]
    assert insert_call["config"]["genre"] == "sci-fi"
    assert insert_call["config"]["chapters"] == 12
    assert insert_call["config"]["title"] == "Override Title"
