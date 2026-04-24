"""Standardized HTTP exception classes for all API endpoints.

All exceptions produce a consistent ``{"error": str, "code": str}`` detail
structure so that clients can branch on machine-readable codes instead of
parsing human-readable message strings.
"""
from __future__ import annotations

from typing import Any

from fastapi import HTTPException


class AppException(HTTPException):
    """Base exception that produces ``{"error": message, "code": error_code}`` detail.

    Subclass this to create domain-specific exceptions.  Pass *detail* to merge
    additional fields (e.g. ``{"field": "email", "valid_transitions": [...]}``)
    into the response body alongside ``error`` and ``code``.
    """

    def __init__(
        self,
        status_code: int,
        error_code: str,
        message: str,
        detail: dict[str, Any] | None = None,
    ) -> None:
        structured_detail: dict[str, Any] = {
            "error": message,
            "code": error_code,
        }
        if detail:
            structured_detail.update(detail)
        super().__init__(status_code=status_code, detail=structured_detail)


# ---------------------------------------------------------------------------
# Domain-specific exceptions
# ---------------------------------------------------------------------------


class JobNotFoundError(AppException):
    """Raised when a job ID does not exist in the database."""

    def __init__(self, job_id: str) -> None:
        super().__init__(
            status_code=404,
            error_code="JOB_NOT_FOUND",
            message=f"Job {job_id} not found",
        )


class ChapterNotFoundError(AppException):
    """Raised when a chapter (job_id + index) does not exist."""

    def __init__(self, job_id: str, index: int) -> None:
        super().__init__(
            status_code=404,
            error_code="CHAPTER_NOT_FOUND",
            message=f"Chapter {index} not found for job {job_id}",
        )


class TemplateNotFoundError(AppException):
    """Raised when a template ID does not exist."""

    def __init__(self, template_id: str) -> None:
        super().__init__(
            status_code=404,
            error_code="TEMPLATE_NOT_FOUND",
            message=f"Template {template_id} not found",
        )


class InvalidStateTransitionError(AppException):
    """Raised when a state machine transition is not allowed."""

    def __init__(
        self,
        current: str,
        target: str,
        valid_transitions: list[str] | None = None,
    ) -> None:
        extra: dict[str, Any] = {}
        if valid_transitions is not None:
            extra["valid_transitions"] = valid_transitions
        super().__init__(
            status_code=409,
            error_code="INVALID_STATE_TRANSITION",
            message=f"Cannot transition from {current} to {target}",
            detail=extra,
        )


class InvalidProviderError(AppException):
    """Raised when an unknown LLM or image provider is specified."""

    def __init__(self, provider: str, provider_type: str) -> None:
        super().__init__(
            status_code=400,
            error_code="INVALID_PROVIDER",
            message=f"Unknown {provider_type} provider: {provider}",
        )


class AppValidationError(AppException):
    """Raised when request data fails domain-level validation.

    Use FastAPI's built-in 422 for schema validation; use this for
    semantic validation after the schema is parsed.
    """

    def __init__(self, message: str, field: str | None = None) -> None:
        extra: dict[str, Any] = {}
        if field is not None:
            extra["field"] = field
        super().__init__(
            status_code=422,
            error_code="VALIDATION_ERROR",
            message=message,
            detail=extra,
        )


class ConflictError(AppException):
    """Raised when a resource already exists or a uniqueness constraint fails."""

    def __init__(self, message: str, code: str = "CONFLICT") -> None:
        super().__init__(
            status_code=409,
            error_code=code,
            message=message,
        )


class NoCoverAwaitingApprovalError(AppException):
    """Raised when a cover action requires awaiting_approval status but it is not."""

    def __init__(self) -> None:
        super().__init__(
            status_code=409,
            error_code="NO_PENDING_COVER",
            message="No cover awaiting approval",
        )


class EmptyBatchError(AppException):
    """Raised when a batch submission contains no valid jobs."""

    def __init__(self) -> None:
        super().__init__(
            status_code=422,
            error_code="EMPTY_BATCH",
            message="No valid jobs in batch",
        )


class InternalError(AppException):
    """Raised for unexpected server-side failures where a safe message is needed."""

    def __init__(self, message: str) -> None:
        super().__init__(
            status_code=500,
            error_code="INTERNAL_ERROR",
            message=message,
        )
