"""Security utilities including centralized secret redaction.

This module is the single source of truth for redacting sensitive fields
from API responses. Import ``redact_sensitive_fields`` from here in every
route that may return data containing credentials or secrets.
"""
from __future__ import annotations

from typing import Any

# Keys whose values must NEVER appear in an API response.
# Matching is case-insensitive; extend this set to add new sensitive fields.
SENSITIVE_KEYS: frozenset[str] = frozenset({
    "api_key",
    "llm_api_key",
    "image_api_key",
    "password",
    "token",
    "secret",
    "authorization",
})

_REDACTED = "***REDACTED***"


def redact_sensitive_fields(obj: Any) -> Any:
    """Recursively redact sensitive fields from dicts and lists.

    Returns a new object with any key whose lower-cased name appears in
    ``SENSITIVE_KEYS`` replaced with ``"***REDACTED***"``.  The original
    object is never mutated.

    Args:
        obj: A ``dict``, ``list``, or any scalar value.

    Returns:
        A deep copy of *obj* with sensitive values replaced.  Scalars
        (str, int, float, bool, None, …) are returned unchanged.
    """
    if isinstance(obj, dict):
        result: dict[str, Any] = {}
        for key, value in obj.items():
            if key.lower() in SENSITIVE_KEYS:
                result[key] = _REDACTED
            else:
                result[key] = redact_sensitive_fields(value)
        return result

    if isinstance(obj, list):
        return [redact_sensitive_fields(item) for item in obj]

    return obj
