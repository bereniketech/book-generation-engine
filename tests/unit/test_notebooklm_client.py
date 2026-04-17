"""Unit tests for NotebookLMClient."""
from unittest.mock import MagicMock, patch

import pytest

from worker.clients.notebooklm_client import NotebookLMClient


def test_research_happy_path_returns_summary():
    create_resp = MagicMock()
    create_resp.raise_for_status.return_value = None
    create_resp.json.return_value = {"name": "notebooks/nb-abc"}

    source_resp = MagicMock()
    source_resp.raise_for_status.return_value = None
    source_resp.json.return_value = {"id": "src-1"}

    poll_resp = MagicMock()
    poll_resp.raise_for_status.return_value = None
    poll_resp.json.return_value = {"summary": "Deep research summary about Stoicism."}

    with patch("worker.clients.notebooklm_client.httpx.Client") as MockClient, \
         patch("worker.clients.notebooklm_client.time.sleep"):

        call_count = 0

        def client_factory(*args, **kwargs):
            nonlocal call_count
            m = MagicMock()
            m.__enter__ = lambda s: m
            m.__exit__ = MagicMock(return_value=False)
            if call_count == 0:
                m.post = MagicMock(return_value=create_resp)
            elif call_count == 1:
                m.post = MagicMock(return_value=source_resp)
            else:
                m.get = MagicMock(return_value=poll_resp)
            call_count += 1
            return m

        MockClient.side_effect = client_factory
        client = NotebookLMClient(api_key="test-key")
        result = client.research("Stoicism and modern leadership", max_wait_seconds=10)

    assert result == "Deep research summary about Stoicism."


def test_research_returns_none_when_api_unavailable():
    """When the API raises a network error, research() returns None without raising."""
    import httpx as _httpx

    with patch("worker.clients.notebooklm_client.httpx.Client") as MockClient:
        mock_ctx = MagicMock()
        mock_ctx.__enter__ = lambda s: mock_ctx
        mock_ctx.__exit__ = MagicMock(return_value=False)
        mock_ctx.post = MagicMock(
            side_effect=_httpx.ConnectError("Connection refused")
        )
        MockClient.return_value = mock_ctx

        client = NotebookLMClient(api_key="test-key")
        result = client.research("Any topic", max_wait_seconds=10)

    assert result is None


def test_research_returns_none_on_timeout():
    """When polling times out, research() returns None."""
    create_resp = MagicMock()
    create_resp.raise_for_status.return_value = None
    create_resp.json.return_value = {"name": "notebooks/nb-xyz"}

    source_resp = MagicMock()
    source_resp.raise_for_status.return_value = None

    poll_resp = MagicMock()
    poll_resp.raise_for_status.return_value = None
    poll_resp.json.return_value = {"summary": None}

    with patch("worker.clients.notebooklm_client.httpx.Client") as MockClient, \
         patch("worker.clients.notebooklm_client.time.sleep"), \
         patch("worker.clients.notebooklm_client.time.time", side_effect=[0, 0, 999, 999]):

        call_count = 0

        def client_factory(*args, **kwargs):
            nonlocal call_count
            m = MagicMock()
            m.__enter__ = lambda s: m
            m.__exit__ = MagicMock(return_value=False)
            if call_count == 0:
                m.post = MagicMock(return_value=create_resp)
            elif call_count == 1:
                m.post = MagicMock(return_value=source_resp)
            else:
                m.get = MagicMock(return_value=poll_resp)
            call_count += 1
            return m

        MockClient.side_effect = client_factory
        client = NotebookLMClient(api_key="test-key")
        result = client.research("Any topic", max_wait_seconds=1)

    assert result is None
