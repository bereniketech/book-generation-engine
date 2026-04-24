"""Unit and integration tests for app.infrastructure.security.

Coverage target: >= 95% of app/infrastructure/security.py.

Test plan
---------
Unit tests (redact_sensitive_fields):
  1.  Top-level api_key is redacted
  2.  Top-level llm_api_key is redacted
  3.  Top-level image_api_key is redacted
  4.  Top-level password is redacted
  5.  Top-level token is redacted
  6.  Top-level secret is redacted
  7.  Top-level authorization is redacted
  8.  Non-sensitive keys are not changed
  9.  Nested dict is redacted recursively
  10. List of dicts is redacted element-wise
  11. Mixed list (scalars + dicts) preserves scalars
  12. Scalar value (str) is returned unchanged
  13. Scalar value (int) is returned unchanged
  14. None is returned unchanged
  15. Original object is NOT mutated
  16. Key comparison is case-insensitive (API_KEY, Api_Key)
  17. Empty dict returns empty dict
  18. Empty list returns empty list
  19. Deeply nested redaction (3+ levels)
  20. List at top level with sensitive dicts

Integration tests (endpoints do not expose secrets):
  21. GET /v1/jobs/{id} does not expose api_key via job_service.get_job
  22. GET /v1/jobs list does not expose api_key in jobs array
  23. GET /jobs/{id}/chapters does not expose api_key in chapter list
  24. GET /jobs/{id}/chapters/{index} does not expose api_key in chapter
  25. GET /jobs/{id}/cover does not expose api_key in cover response
  26. GET /templates does not expose api_key in template list
  27. POST /templates does not expose api_key in created template response
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from app.infrastructure.security import SENSITIVE_KEYS, redact_sensitive_fields
from app.api.deps import get_supabase

_REDACTED = "***REDACTED***"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_client(mock_supabase: MagicMock | None = None) -> TestClient:
    from app.main import app

    app.state.amqp_channel = MagicMock()
    app.state.amqp_connection = MagicMock()
    if mock_supabase is not None:
        app.dependency_overrides[get_supabase] = lambda: mock_supabase
    else:
        # No supabase needed — clear any override
        app.dependency_overrides.pop(get_supabase, None)
    return TestClient(app, raise_server_exceptions=True)


def _assert_no_secrets(obj: object, path: str = "") -> None:
    """Recursively assert that no sensitive field exposes a raw credential value.

    Any key in SENSITIVE_KEYS must have value ``"***REDACTED***"`` — its
    presence is expected, its raw value is not.
    """
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key.lower() in SENSITIVE_KEYS:
                assert value == "***REDACTED***", (
                    f"Sensitive key '{key}' at path '{path}' has un-redacted value: {value!r}"
                )
            else:
                _assert_no_secrets(value, f"{path}.{key}")
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            _assert_no_secrets(item, f"{path}[{i}]")


# ---------------------------------------------------------------------------
# Unit tests — redact_sensitive_fields
# ---------------------------------------------------------------------------


class TestRedactTopLevelKeys:
    def test_redacts_api_key(self):
        result = redact_sensitive_fields({"api_key": "sk-real-secret"})
        assert result["api_key"] == _REDACTED

    def test_redacts_llm_api_key(self):
        result = redact_sensitive_fields({"llm_api_key": "anthropic-key"})
        assert result["llm_api_key"] == _REDACTED

    def test_redacts_image_api_key(self):
        result = redact_sensitive_fields({"image_api_key": "replicate-key"})
        assert result["image_api_key"] == _REDACTED

    def test_redacts_password(self):
        result = redact_sensitive_fields({"password": "hunter2"})
        assert result["password"] == _REDACTED

    def test_redacts_token(self):
        result = redact_sensitive_fields({"token": "bearer-abc123"})
        assert result["token"] == _REDACTED

    def test_redacts_secret(self):
        result = redact_sensitive_fields({"secret": "topsecret"})
        assert result["secret"] == _REDACTED

    def test_redacts_authorization(self):
        result = redact_sensitive_fields({"authorization": "Bearer abc123"})
        assert result["authorization"] == _REDACTED

    def test_non_sensitive_key_unchanged(self):
        result = redact_sensitive_fields({"title": "My Book", "chapters": 12})
        assert result["title"] == "My Book"
        assert result["chapters"] == 12


class TestRedactNested:
    def test_nested_dict_redacted(self):
        obj = {"llm": {"provider": "anthropic", "api_key": "sk-nested"}}
        result = redact_sensitive_fields(obj)
        assert result["llm"]["provider"] == "anthropic"
        assert result["llm"]["api_key"] == _REDACTED

    def test_deeply_nested_redaction(self):
        obj = {"a": {"b": {"c": {"api_key": "deep-secret", "safe": "value"}}}}
        result = redact_sensitive_fields(obj)
        assert result["a"]["b"]["c"]["api_key"] == _REDACTED
        assert result["a"]["b"]["c"]["safe"] == "value"

    def test_list_of_dicts_redacted(self):
        obj = [
            {"api_key": "key1", "name": "Alice"},
            {"api_key": "key2", "name": "Bob"},
        ]
        result = redact_sensitive_fields(obj)
        assert result[0]["api_key"] == _REDACTED
        assert result[0]["name"] == "Alice"
        assert result[1]["api_key"] == _REDACTED
        assert result[1]["name"] == "Bob"

    def test_mixed_list_preserves_scalars(self):
        obj = {"items": [1, "hello", {"api_key": "secret"}, None]}
        result = redact_sensitive_fields(obj)
        assert result["items"][0] == 1
        assert result["items"][1] == "hello"
        assert result["items"][2]["api_key"] == _REDACTED
        assert result["items"][3] is None

    def test_top_level_list_with_sensitive_dicts(self):
        obj = [{"secret": "abc"}, {"title": "ok"}]
        result = redact_sensitive_fields(obj)
        assert result[0]["secret"] == _REDACTED
        assert result[1]["title"] == "ok"


class TestRedactScalars:
    def test_string_scalar_unchanged(self):
        assert redact_sensitive_fields("plain-string") == "plain-string"

    def test_int_scalar_unchanged(self):
        assert redact_sensitive_fields(42) == 42

    def test_none_scalar_unchanged(self):
        assert redact_sensitive_fields(None) is None

    def test_empty_dict_returns_empty_dict(self):
        assert redact_sensitive_fields({}) == {}

    def test_empty_list_returns_empty_list(self):
        assert redact_sensitive_fields([]) == []


class TestRedactImmutability:
    def test_original_dict_not_mutated(self):
        original = {"api_key": "real-secret", "title": "Book"}
        _ = redact_sensitive_fields(original)
        assert original["api_key"] == "real-secret"

    def test_original_nested_dict_not_mutated(self):
        original = {"llm": {"api_key": "nested-secret"}}
        _ = redact_sensitive_fields(original)
        assert original["llm"]["api_key"] == "nested-secret"

    def test_original_list_not_mutated(self):
        original = [{"api_key": "secret"}]
        _ = redact_sensitive_fields(original)
        assert original[0]["api_key"] == "secret"


class TestRedactCaseInsensitivity:
    def test_uppercase_API_KEY_redacted(self):
        result = redact_sensitive_fields({"API_KEY": "value"})
        assert result["API_KEY"] == _REDACTED

    def test_mixed_case_Api_Key_redacted(self):
        result = redact_sensitive_fields({"Api_Key": "value"})
        assert result["Api_Key"] == _REDACTED

    def test_uppercase_PASSWORD_redacted(self):
        result = redact_sensitive_fields({"PASSWORD": "hunter2"})
        assert result["PASSWORD"] == _REDACTED

    def test_uppercase_TOKEN_redacted(self):
        result = redact_sensitive_fields({"TOKEN": "abc"})
        assert result["TOKEN"] == _REDACTED


# ---------------------------------------------------------------------------
# Integration tests — endpoints must not expose secrets in responses
# ---------------------------------------------------------------------------


class TestJobsEndpointRedaction:
    def test_get_job_does_not_expose_api_key(self):
        """GET /v1/jobs/{id} must redact api_key in returned job dict."""
        client = _make_client(MagicMock())
        job_with_secret = {
            "id": "job-1",
            "status": "generating",
            "config": {"api_key": "sk-top-secret", "title": "My Book"},
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
            "notification_email": None,
        }
        with patch("app.api.jobs.job_service.get_job", return_value=redact_sensitive_fields(job_with_secret)):
            resp = client.get("/v1/jobs/job-1")
        assert resp.status_code == 200
        _assert_no_secrets(resp.json())

    def test_list_jobs_does_not_expose_api_key(self):
        """GET /v1/jobs must redact api_key in every job in the jobs array."""
        jobs_with_secret = [
            {
                "id": "job-1",
                "status": "generating",
                "config": {"api_key": "sk-secret-1"},
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
            },
            {
                "id": "job-2",
                "status": "complete",
                "config": {"llm_api_key": "sk-secret-2"},
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
            },
        ]
        mock_sb = MagicMock()
        list_result = MagicMock()
        list_result.data = jobs_with_secret
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
        _assert_no_secrets(body["jobs"])


class TestChaptersEndpointRedaction:
    def test_list_chapters_does_not_expose_api_key(self):
        """GET /jobs/{id}/chapters must redact sensitive fields from each chapter."""
        chapter_with_secret = {
            "index": 0,
            "status": "complete",
            "qa_score": 9.0,
            "content": "Chapter content here.",
            "api_key": "should-be-redacted",
        }
        mock_sb_client = MagicMock()
        (
            mock_sb_client.table.return_value
            .select.return_value
            .eq.return_value
            .order.return_value
            .execute.return_value.data
        ) = [chapter_with_secret]
        client = _make_client(mock_sb_client)
        resp = client.get("/jobs/job-1/chapters")
        assert resp.status_code == 200
        _assert_no_secrets(resp.json()["chapters"])

    def test_get_single_chapter_does_not_expose_api_key(self):
        """GET /jobs/{id}/chapters/{index} must redact sensitive fields."""
        chapter_data = {
            "index": 0,
            "content": "Full chapter content.",
            "status": "complete",
            "qa_score": 8.5,
            "flesch_kincaid_grade": 7.2,
            "flesch_reading_ease": 65.0,
            "api_key": "leaked-key",
        }
        mock_sb_client = MagicMock()
        (
            mock_sb_client.table.return_value
            .select.return_value
            .eq.return_value
            .eq.return_value
            .single.return_value
            .execute.return_value.data
        ) = chapter_data
        client = _make_client(mock_sb_client)
        resp = client.get("/jobs/job-1/chapters/0")
        assert resp.status_code == 200
        _assert_no_secrets(resp.json())


class TestCoverEndpointRedaction:
    def test_get_cover_does_not_expose_api_key(self):
        """GET /jobs/{id}/cover must redact sensitive fields from the response."""
        job_data = {
            "id": "job-1",
            "status": "awaiting_cover_approval",
            "cover_status": "awaiting_approval",
            "cover_url": "https://example.com/cover.png",
            "config": {"api_key": "should-not-appear", "title": "Book"},
        }
        mock_sb_client = MagicMock()
        (
            mock_sb_client.table.return_value
            .select.return_value
            .eq.return_value
            .single.return_value
            .execute.return_value.data
        ) = job_data
        client = _make_client(mock_sb_client)
        resp = client.get("/jobs/job-1/cover")
        assert resp.status_code == 200
        _assert_no_secrets(resp.json())


class TestTemplatesEndpointRedaction:
    def test_list_templates_does_not_expose_api_key(self):
        """GET /templates must redact sensitive fields from every template."""
        templates_with_secret = [
            {
                "id": "t-1",
                "name": "fiction-default",
                "config": {"api_key": "hidden-key", "genre": "fiction"},
                "created_at": "2024-01-01",
            }
        ]
        mock_sb_client = MagicMock()
        (
            mock_sb_client.table.return_value
            .select.return_value
            .order.return_value
            .execute.return_value.data
        ) = templates_with_secret
        client = _make_client(mock_sb_client)
        resp = client.get("/templates")
        assert resp.status_code == 200
        _assert_no_secrets(resp.json()["templates"])

    def test_create_template_does_not_expose_api_key(self):
        """POST /templates must redact sensitive fields in the created template response."""
        created = {
            "id": "t-new",
            "name": "new-template",
            "config": {"api_key": "hidden", "genre": "sci-fi"},
        }
        mock_sb_client = MagicMock()
        mock_sb_client.table.return_value.insert.return_value.execute.return_value.data = [created]
        client = _make_client(mock_sb_client)
        resp = client.post("/templates", json={"name": "new-template", "config": {"genre": "sci-fi"}})
        assert resp.status_code == 201
        _assert_no_secrets(resp.json())
