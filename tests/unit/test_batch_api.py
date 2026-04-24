"""Unit tests for batch job submission."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_batch_submit_json_valid_jobs():
    mock_supabase = MagicMock()
    mock_supabase.table.return_value.select.return_value.in_.return_value.execute.return_value.count = 0
    mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [{"id": "job-abc"}]

    mock_connection = AsyncMock()
    mock_channel = AsyncMock()
    mock_connection.channel.return_value = mock_channel
    mock_exchange = AsyncMock()
    mock_channel.get_exchange.return_value = mock_exchange

    with patch("app.api.batch.get_supabase_client", return_value=mock_supabase), \
         patch("aio_pika.connect_robust", return_value=mock_connection):
        resp = client.post("/batch", json={
            "format": "json",
            "jobs": [{"title": "Book One", "genre": "fiction"}, {"title": "Book Two", "genre": "non-fiction"}]
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

    mock_connection = AsyncMock()
    mock_channel = AsyncMock()
    mock_connection.channel.return_value = mock_channel
    mock_exchange = AsyncMock()
    mock_channel.get_exchange.return_value = mock_exchange

    with patch("app.api.batch.get_supabase_client", return_value=mock_supabase), \
         patch("aio_pika.connect_robust", return_value=mock_connection):
        resp = client.post("/batch", json={
            "format": "json",
            "jobs": [
                {"title": "Valid Book", "genre": "fiction"},
                {"bad_field": "no title or genre"}
            ]
        })

    assert resp.status_code == 200
    data = resp.json()
    assert data["enqueued"] == 1
    assert data["skipped"] == 1
    assert len(data["errors"]) == 1
    assert data["errors"][0]["row"] == 1


def test_batch_all_invalid_returns_422():
    mock_supabase = MagicMock()
    mock_supabase.table.return_value.select.return_value.in_.return_value.execute.return_value.count = 0

    mock_connection = AsyncMock()
    mock_channel = AsyncMock()
    mock_connection.channel.return_value = mock_channel

    with patch("app.api.batch.get_supabase_client", return_value=mock_supabase), \
         patch("aio_pika.connect_robust", return_value=mock_connection):
        resp = client.post("/batch", json={
            "format": "json",
            "jobs": [{"bad": "no title"}, {"also_bad": "missing"}]
        })

    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "EMPTY_BATCH"
