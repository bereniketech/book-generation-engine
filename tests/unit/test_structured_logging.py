"""Verify structlog configuration produces JSON output with required fields."""
import json
import sys
from io import StringIO

import structlog
import pytest

from app.core.logging import setup_logging, get_logger


def test_setup_logging_does_not_raise():
    setup_logging(log_level="DEBUG")


def test_get_logger_returns_bound_logger():
    setup_logging()
    log = get_logger("test")
    assert log is not None


def test_log_output_is_valid_json(capsys):
    setup_logging(log_level="DEBUG")
    log = get_logger("test")
    log.info("test.event", job_id="abc-123", stage="planning", duration_ms=42)
    captured = capsys.readouterr()
    lines = [l for l in captured.out.strip().splitlines() if l]
    assert len(lines) >= 1
    record = json.loads(lines[-1])
    assert record["event"] == "test.event"
    assert record["job_id"] == "abc-123"
    assert record["stage"] == "planning"
    assert record["duration_ms"] == 42
    assert "timestamp" in record
    assert "level" in record


def test_log_level_info_suppresses_debug(capsys):
    setup_logging(log_level="INFO")
    log = get_logger("test")
    log.debug("debug.event", job_id="x")
    captured = capsys.readouterr()
    assert "debug.event" not in captured.out
