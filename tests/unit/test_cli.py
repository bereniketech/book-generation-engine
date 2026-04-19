"""Unit tests for bookgen CLI commands."""
import json
import pytest
from pathlib import Path
from typer.testing import CliRunner
from unittest.mock import MagicMock, patch
import httpx

from cli.main import app

runner = CliRunner()


def test_submit_missing_config_file_exits_1(tmp_path):
    result = runner.invoke(app, ["submit", "--config", str(tmp_path / "nonexistent.json")])
    assert result.exit_code == 1
    assert "not found" in result.output


def test_submit_valid_config_prints_job_id(tmp_path):
    config_file = tmp_path / "job.json"
    config_file.write_text(json.dumps({"title": "Test Book", "genre": "fiction"}))

    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.json.return_value = {"id": "new-job-uuid"}

    with patch("cli.main._client") as mock_client_ctx:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_client_ctx.return_value = mock_client
        result = runner.invoke(app, ["submit", "--config", str(config_file)])

    assert result.exit_code == 0
    assert "new-job-uuid" in result.output


def test_list_prints_table():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "jobs": [{"id": "j-1", "status": "generating", "created_at": "2024-01-01"}],
        "total": 1,
    }

    with patch("cli.main._client") as mock_client_ctx:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_response
        mock_client_ctx.return_value = mock_client
        result = runner.invoke(app, ["list"])

    assert result.exit_code == 0
    assert "j-1" in result.output
    assert "generating" in result.output


def test_cancel_prints_confirmation():
    mock_response = MagicMock()
    mock_response.status_code = 204

    with patch("cli.main._client") as mock_client_ctx:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.delete.return_value = mock_response
        mock_client_ctx.return_value = mock_client
        result = runner.invoke(app, ["cancel", "job-123"])

    assert result.exit_code == 0
    assert "cancelled" in result.output.lower()


def test_connect_error_exits_1():
    with patch("cli.main._client") as mock_client_ctx:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.side_effect = httpx.ConnectError("connection refused")
        mock_client_ctx.return_value = mock_client
        result = runner.invoke(app, ["list"])

    assert result.exit_code == 1
    assert "Cannot connect" in result.output
