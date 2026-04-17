"""NotebookLM API client for non-fiction deep research.

Graceful fallback: returns None on any network or API error.
The non-fiction pipeline synthesises a research summary via LLM when None is returned.
"""
from __future__ import annotations

import logging
import time

import httpx

logger = logging.getLogger(__name__)

NOTEBOOKLM_API_BASE = "https://notebooklm.googleapis.com/v1"


class NotebookLMClient:
    """Wraps the NotebookLM API. Returns None on failure — never raises."""

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self._headers = {"x-goog-api-key": api_key, "Content-Type": "application/json"}

    def research(self, topic: str, max_wait_seconds: int = 120) -> str | None:
        """Create a notebook, add the topic as a source, and return the generated summary.

        Returns None if the API is unavailable or generation times out.
        """
        try:
            notebook_id = self._create_notebook(topic)
            if notebook_id is None:
                return None
            source_added = self._add_text_source(notebook_id, topic)
            if not source_added:
                return None
            summary = self._wait_for_summary(notebook_id, max_wait_seconds)
            return summary
        except Exception as exc:
            logger.warning("NotebookLM research failed (will use LLM fallback): %s", exc)
            return None

    def _create_notebook(self, title: str) -> str | None:
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    f"{NOTEBOOKLM_API_BASE}/notebooks",
                    headers=self._headers,
                    json={"title": title[:100]},
                )
                response.raise_for_status()
                data = response.json()
                return data.get("name", "").split("/")[-1]
        except Exception as exc:
            logger.warning("NotebookLM create_notebook failed: %s", exc)
            return None

    def _add_text_source(self, notebook_id: str, text: str) -> bool:
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    f"{NOTEBOOKLM_API_BASE}/notebooks/{notebook_id}/sources",
                    headers=self._headers,
                    json={"text_content": {"text": text}},
                )
                response.raise_for_status()
                return True
        except Exception as exc:
            logger.warning("NotebookLM add_source failed: %s", exc)
            return False

    def _wait_for_summary(self, notebook_id: str, max_wait_seconds: int) -> str | None:
        deadline = time.time() + max_wait_seconds
        with httpx.Client(timeout=30.0) as client:
            while time.time() < deadline:
                try:
                    response = client.get(
                        f"{NOTEBOOKLM_API_BASE}/notebooks/{notebook_id}",
                        headers=self._headers,
                    )
                    response.raise_for_status()
                    data = response.json()
                    summary = data.get("summary") or data.get("description")
                    if summary:
                        return str(summary)
                except Exception as exc:
                    logger.warning("NotebookLM poll failed: %s", exc)
                time.sleep(5)
        logger.warning("NotebookLM summary timed out after %ds", max_wait_seconds)
        return None
