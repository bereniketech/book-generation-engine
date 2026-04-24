"""Structured logging configuration using structlog with JSON output."""
from __future__ import annotations

import logging
import sys
from typing import Any

import structlog


_KNOWN_LEVELS: frozenset[str] = frozenset({"debug", "info", "warning", "error", "critical"})


def safe_log(level: int, event: str, **kwargs: Any) -> None:
    """Emit a structured log entry without ever raising.

    Uses the module-level structlog bound logger internally.  All
    kwargs are forwarded as structured fields.  If the underlying
    logger raises for any reason (e.g. a non-serialisable value in a
    ``structlog`` context, a ``ValueError`` from the bound-logger
    wrapper, or any other exception) the failure is silently swallowed
    so that a logging error can never interrupt business logic.

    Args:
        level: A :mod:`logging` level constant (e.g. ``logging.INFO``).
        event: The event name / message string.
        **kwargs: Arbitrary structured fields forwarded to the logger.
    """
    try:
        _log = structlog.get_logger(__name__)
        # structlog bound loggers expose level methods by name, not by
        # integer constant.  Translate the integer to a lowercase name and
        # validate it is a known structlog method before calling it.
        method_name = logging.getLevelName(level).lower()
        if method_name not in _KNOWN_LEVELS:
            # Unknown level — fall back to info so we still emit something.
            method_name = "info"
        log_method = getattr(_log, method_name)
        log_method(event, **kwargs)
    except Exception:  # noqa: BLE001 — intentionally broad; logging must never raise
        pass


def setup_logging(log_level: str = "INFO") -> None:
    """Configure structlog for JSON output. Call once at application startup.

    After calling this, use:
        log = structlog.get_logger()
        log.info("event.name", job_id=job_id, stage="planning", duration_ms=123)
    """
    def _safe_add_logger_name(
        logger: object,
        method_name: str,
        event_dict: structlog.types.EventDict,
    ) -> structlog.types.EventDict:
        """Add logger name when available (PrintLogger has no .name attribute)."""
        name = getattr(logger, "name", None)
        if name is not None:
            event_dict["logger"] = name
        return event_dict

    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        _safe_add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(log_level.upper())
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )

    # Silence noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("aio_pika").setLevel(logging.WARNING)
    logging.getLogger("aiormq").setLevel(logging.WARNING)


def get_logger(name: str | None = None) -> structlog.BoundLogger:
    """Return a structlog bound logger. Use instead of logging.getLogger()."""
    return structlog.get_logger(name)
