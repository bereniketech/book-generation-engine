"""Unit tests for app.core.logging.safe_log defensive logging utility."""
from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

import pytest
import structlog

from app.core.logging import safe_log, setup_logging


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _NonSerializable:
    """Object whose __str__ raises, simulating a pathologically bad kwarg value."""

    def __str__(self) -> str:
        raise RuntimeError("cannot serialise")

    def __repr__(self) -> str:
        raise RuntimeError("cannot serialise")


# ---------------------------------------------------------------------------
# Core contract: safe_log NEVER raises
# ---------------------------------------------------------------------------

class TestSafeLogNeverRaises:
    """safe_log must swallow every exception so business logic is unaffected."""

    def test_does_not_raise_on_normal_call(self):
        setup_logging()
        safe_log(logging.INFO, "test.event", key="value")

    def test_does_not_raise_with_non_serializable_kwarg(self):
        setup_logging()
        safe_log(logging.INFO, "test.event", obj=_NonSerializable())

    def test_does_not_raise_when_structlog_raises_value_error(self):
        """Simulates the exact ValueError that was previously silenced with try/except pass."""
        with patch("structlog.get_logger") as mock_get_logger:
            mock_logger = MagicMock()
            mock_logger.info.side_effect = ValueError("structlog context error")
            mock_get_logger.return_value = mock_logger
            # Must not propagate the ValueError
            safe_log(logging.INFO, "api.job.created", job_id="abc")

    def test_does_not_raise_when_structlog_raises_runtime_error(self):
        with patch("structlog.get_logger") as mock_get_logger:
            mock_logger = MagicMock()
            mock_logger.warning.side_effect = RuntimeError("unexpected")
            mock_get_logger.return_value = mock_logger
            safe_log(logging.WARNING, "batch.row.skipped", row=0)

    def test_does_not_raise_when_structlog_raises_type_error(self):
        with patch("structlog.get_logger") as mock_get_logger:
            mock_logger = MagicMock()
            mock_logger.error.side_effect = TypeError("bad arg")
            mock_get_logger.return_value = mock_logger
            safe_log(logging.ERROR, "token_usage.record_failed", job_id="abc")

    def test_does_not_raise_when_get_logger_itself_raises(self):
        with patch("structlog.get_logger", side_effect=Exception("unavailable")):
            safe_log(logging.INFO, "some.event", key="value")


# ---------------------------------------------------------------------------
# Level routing: correct structlog method is called for each logging level
# ---------------------------------------------------------------------------

class TestSafeLogLevelRouting:
    """safe_log maps stdlib logging level integers to structlog method names."""

    def _patched_logger(self):
        mock_logger = MagicMock()
        return mock_logger

    def test_info_level_calls_info_method(self):
        with patch("structlog.get_logger") as mock_get_logger:
            mock_logger = self._patched_logger()
            mock_get_logger.return_value = mock_logger
            safe_log(logging.INFO, "test.info", key="v")
            mock_logger.info.assert_called_once_with("test.info", key="v")

    def test_debug_level_calls_debug_method(self):
        with patch("structlog.get_logger") as mock_get_logger:
            mock_logger = self._patched_logger()
            mock_get_logger.return_value = mock_logger
            safe_log(logging.DEBUG, "test.debug", key="v")
            mock_logger.debug.assert_called_once_with("test.debug", key="v")

    def test_warning_level_calls_warning_method(self):
        with patch("structlog.get_logger") as mock_get_logger:
            mock_logger = self._patched_logger()
            mock_get_logger.return_value = mock_logger
            safe_log(logging.WARNING, "test.warning", key="v")
            mock_logger.warning.assert_called_once_with("test.warning", key="v")

    def test_error_level_calls_error_method(self):
        with patch("structlog.get_logger") as mock_get_logger:
            mock_logger = self._patched_logger()
            mock_get_logger.return_value = mock_logger
            safe_log(logging.ERROR, "test.error", key="v")
            mock_logger.error.assert_called_once_with("test.error", key="v")

    def test_critical_level_calls_critical_method(self):
        with patch("structlog.get_logger") as mock_get_logger:
            mock_logger = self._patched_logger()
            mock_get_logger.return_value = mock_logger
            safe_log(logging.CRITICAL, "test.critical", key="v")
            mock_logger.critical.assert_called_once_with("test.critical", key="v")

    def test_unknown_level_falls_back_to_info(self):
        """An unrecognised integer level must not crash; it falls back to info."""
        with patch("structlog.get_logger") as mock_get_logger:
            mock_logger = self._patched_logger()
            mock_get_logger.return_value = mock_logger
            safe_log(99999, "test.unknown_level", key="v")
            mock_logger.info.assert_called_once_with("test.unknown_level", key="v")


# ---------------------------------------------------------------------------
# Kwargs forwarding: all keyword arguments reach the logger
# ---------------------------------------------------------------------------

class TestSafeLogKwargsForwarding:
    """safe_log must forward all kwargs as structured fields."""

    def test_forwards_single_kwarg(self):
        with patch("structlog.get_logger") as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            safe_log(logging.INFO, "event", job_id="x123")
            mock_logger.info.assert_called_once_with("event", job_id="x123")

    def test_forwards_multiple_kwargs(self):
        with patch("structlog.get_logger") as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            safe_log(
                logging.INFO,
                "api.job.created",
                job_id="abc",
                has_template=True,
                stage="queued",
            )
            mock_logger.info.assert_called_once_with(
                "api.job.created",
                job_id="abc",
                has_template=True,
                stage="queued",
            )

    def test_forwards_no_kwargs(self):
        with patch("structlog.get_logger") as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            safe_log(logging.INFO, "bare.event")
            mock_logger.info.assert_called_once_with("bare.event")


# ---------------------------------------------------------------------------
# Integration: actual structlog output does not raise end-to-end
# ---------------------------------------------------------------------------

class TestSafeLogIntegration:
    """End-to-end smoke tests using the real structlog pipeline."""

    def test_emits_output_for_normal_event(self, capsys):
        setup_logging(log_level="DEBUG")
        safe_log(logging.DEBUG, "integration.event", job_id="z999", stage="test")
        captured = capsys.readouterr()
        assert "integration.event" in captured.out

    def test_emits_no_output_when_level_below_threshold(self, capsys):
        setup_logging(log_level="WARNING")
        safe_log(logging.DEBUG, "suppressed.debug.event")
        captured = capsys.readouterr()
        assert "suppressed.debug.event" not in captured.out
