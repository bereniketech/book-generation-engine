"""Unit tests for standardized HTTP exception classes.

Verifies that every exception class produces the correct status code,
error code, and detail structure so that API clients can rely on a
consistent ``{"error": str, "code": str}`` envelope.
"""
from __future__ import annotations

import pytest

from app.infrastructure.http_exceptions import (
    AppException,
    AppValidationError,
    ChapterNotFoundError,
    ConflictError,
    EmptyBatchError,
    InternalError,
    InvalidProviderError,
    InvalidStateTransitionError,
    JobNotFoundError,
    NoCoverAwaitingApprovalError,
    TemplateNotFoundError,
)


# ---------------------------------------------------------------------------
# AppException base class
# ---------------------------------------------------------------------------


class TestAppException:
    def test_produces_structured_detail(self):
        exc = AppException(status_code=400, error_code="TEST_CODE", message="Test message")
        assert exc.detail["error"] == "Test message"
        assert exc.detail["code"] == "TEST_CODE"
        assert exc.status_code == 400

    def test_merges_extra_detail_fields(self):
        exc = AppException(
            status_code=409,
            error_code="CONFLICT",
            message="Conflict occurred",
            detail={"field": "email", "hint": "use unique email"},
        )
        assert exc.detail["error"] == "Conflict occurred"
        assert exc.detail["code"] == "CONFLICT"
        assert exc.detail["field"] == "email"
        assert exc.detail["hint"] == "use unique email"

    def test_none_detail_does_not_add_extra_keys(self):
        exc = AppException(status_code=404, error_code="NOT_FOUND", message="missing", detail=None)
        assert set(exc.detail.keys()) == {"error", "code"}

    def test_empty_detail_dict_does_not_add_extra_keys(self):
        exc = AppException(status_code=404, error_code="NOT_FOUND", message="missing", detail={})
        assert set(exc.detail.keys()) == {"error", "code"}


# ---------------------------------------------------------------------------
# JobNotFoundError
# ---------------------------------------------------------------------------


class TestJobNotFoundError:
    def test_status_code_is_404(self):
        exc = JobNotFoundError("abc-123")
        assert exc.status_code == 404

    def test_error_code(self):
        exc = JobNotFoundError("abc-123")
        assert exc.detail["code"] == "JOB_NOT_FOUND"

    def test_message_contains_job_id(self):
        exc = JobNotFoundError("abc-123")
        assert "abc-123" in exc.detail["error"]


# ---------------------------------------------------------------------------
# ChapterNotFoundError
# ---------------------------------------------------------------------------


class TestChapterNotFoundError:
    def test_status_code_is_404(self):
        exc = ChapterNotFoundError("job-1", 3)
        assert exc.status_code == 404

    def test_error_code(self):
        exc = ChapterNotFoundError("job-1", 3)
        assert exc.detail["code"] == "CHAPTER_NOT_FOUND"

    def test_message_contains_index_and_job_id(self):
        exc = ChapterNotFoundError("job-1", 3)
        assert "3" in exc.detail["error"]
        assert "job-1" in exc.detail["error"]


# ---------------------------------------------------------------------------
# TemplateNotFoundError
# ---------------------------------------------------------------------------


class TestTemplateNotFoundError:
    def test_status_code_is_404(self):
        exc = TemplateNotFoundError("tmpl-99")
        assert exc.status_code == 404

    def test_error_code(self):
        exc = TemplateNotFoundError("tmpl-99")
        assert exc.detail["code"] == "TEMPLATE_NOT_FOUND"

    def test_message_contains_template_id(self):
        exc = TemplateNotFoundError("tmpl-99")
        assert "tmpl-99" in exc.detail["error"]


# ---------------------------------------------------------------------------
# InvalidStateTransitionError
# ---------------------------------------------------------------------------


class TestInvalidStateTransitionError:
    def test_status_code_is_409(self):
        exc = InvalidStateTransitionError("complete", "paused")
        assert exc.status_code == 409

    def test_error_code(self):
        exc = InvalidStateTransitionError("complete", "paused")
        assert exc.detail["code"] == "INVALID_STATE_TRANSITION"

    def test_message_contains_states(self):
        exc = InvalidStateTransitionError("complete", "paused")
        assert "complete" in exc.detail["error"]
        assert "paused" in exc.detail["error"]

    def test_valid_transitions_included_when_provided(self):
        exc = InvalidStateTransitionError("complete", "paused", valid_transitions=["queued"])
        assert exc.detail["valid_transitions"] == ["queued"]

    def test_valid_transitions_absent_when_not_provided(self):
        exc = InvalidStateTransitionError("complete", "paused")
        assert "valid_transitions" not in exc.detail

    def test_empty_valid_transitions_list_included(self):
        exc = InvalidStateTransitionError("complete", "paused", valid_transitions=[])
        assert exc.detail["valid_transitions"] == []


# ---------------------------------------------------------------------------
# InvalidProviderError
# ---------------------------------------------------------------------------


class TestInvalidProviderError:
    def test_status_code_is_400(self):
        exc = InvalidProviderError("unknown-llm", "llm")
        assert exc.status_code == 400

    def test_error_code(self):
        exc = InvalidProviderError("unknown-llm", "llm")
        assert exc.detail["code"] == "INVALID_PROVIDER"

    def test_message_contains_provider_and_type(self):
        exc = InvalidProviderError("unknown-llm", "llm")
        assert "unknown-llm" in exc.detail["error"]
        assert "llm" in exc.detail["error"]


# ---------------------------------------------------------------------------
# AppValidationError
# ---------------------------------------------------------------------------


class TestAppValidationError:
    def test_status_code_is_422(self):
        exc = AppValidationError("must be positive")
        assert exc.status_code == 422

    def test_error_code(self):
        exc = AppValidationError("must be positive")
        assert exc.detail["code"] == "VALIDATION_ERROR"

    def test_field_included_when_provided(self):
        exc = AppValidationError("must be positive", field="count")
        assert exc.detail["field"] == "count"

    def test_field_absent_when_not_provided(self):
        exc = AppValidationError("must be positive")
        assert "field" not in exc.detail


# ---------------------------------------------------------------------------
# ConflictError
# ---------------------------------------------------------------------------


class TestConflictError:
    def test_status_code_is_409(self):
        exc = ConflictError("already exists")
        assert exc.status_code == 409

    def test_default_error_code(self):
        exc = ConflictError("already exists")
        assert exc.detail["code"] == "CONFLICT"

    def test_custom_error_code(self):
        exc = ConflictError("template exists", code="TEMPLATE_EXISTS")
        assert exc.detail["code"] == "TEMPLATE_EXISTS"

    def test_message_preserved(self):
        exc = ConflictError("already exists")
        assert exc.detail["error"] == "already exists"


# ---------------------------------------------------------------------------
# NoCoverAwaitingApprovalError
# ---------------------------------------------------------------------------


class TestNoCoverAwaitingApprovalError:
    def test_status_code_is_409(self):
        exc = NoCoverAwaitingApprovalError()
        assert exc.status_code == 409

    def test_error_code(self):
        exc = NoCoverAwaitingApprovalError()
        assert exc.detail["code"] == "NO_PENDING_COVER"

    def test_message(self):
        exc = NoCoverAwaitingApprovalError()
        assert exc.detail["error"] == "No cover awaiting approval"


# ---------------------------------------------------------------------------
# EmptyBatchError
# ---------------------------------------------------------------------------


class TestEmptyBatchError:
    def test_status_code_is_422(self):
        exc = EmptyBatchError()
        assert exc.status_code == 422

    def test_error_code(self):
        exc = EmptyBatchError()
        assert exc.detail["code"] == "EMPTY_BATCH"

    def test_message(self):
        exc = EmptyBatchError()
        assert exc.detail["error"] == "No valid jobs in batch"


# ---------------------------------------------------------------------------
# InternalError
# ---------------------------------------------------------------------------


class TestInternalError:
    def test_status_code_is_500(self):
        exc = InternalError("something went wrong")
        assert exc.status_code == 500

    def test_error_code(self):
        exc = InternalError("something went wrong")
        assert exc.detail["code"] == "INTERNAL_ERROR"

    def test_message_preserved(self):
        exc = InternalError("something went wrong")
        assert exc.detail["error"] == "something went wrong"


# ---------------------------------------------------------------------------
# Structural invariants across all exception types
# ---------------------------------------------------------------------------


class TestStructuralInvariants:
    """Every exception must have 'error' and 'code' keys in detail."""

    _all_exceptions = [
        JobNotFoundError("x"),
        ChapterNotFoundError("j", 0),
        TemplateNotFoundError("t"),
        InvalidStateTransitionError("a", "b"),
        InvalidProviderError("p", "llm"),
        AppValidationError("bad"),
        ConflictError("dupe"),
        NoCoverAwaitingApprovalError(),
        EmptyBatchError(),
        InternalError("oops"),
    ]

    @pytest.mark.parametrize("exc", _all_exceptions)
    def test_detail_has_error_key(self, exc: AppException):
        assert "error" in exc.detail

    @pytest.mark.parametrize("exc", _all_exceptions)
    def test_detail_has_code_key(self, exc: AppException):
        assert "code" in exc.detail

    @pytest.mark.parametrize("exc", _all_exceptions)
    def test_error_is_nonempty_string(self, exc: AppException):
        assert isinstance(exc.detail["error"], str)
        assert len(exc.detail["error"]) > 0

    @pytest.mark.parametrize("exc", _all_exceptions)
    def test_code_is_nonempty_string(self, exc: AppException):
        assert isinstance(exc.detail["code"], str)
        assert len(exc.detail["code"]) > 0
