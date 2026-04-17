"""Unit tests for email_service."""
from unittest.mock import AsyncMock, patch

import pytest

from app.services.email_service import send_completion_email


@pytest.mark.asyncio
async def test_send_completion_email_success():
    with patch("app.services.email_service._send", new_callable=AsyncMock) as mock_send:
        await send_completion_email("test@example.com", "https://example.com/bundle.zip", "My Book")
    mock_send.assert_called_once()


@pytest.mark.asyncio
async def test_send_completion_email_retries_once_on_failure():
    call_count = 0

    async def fail_then_succeed(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise ConnectionError("SMTP connection refused")
        # Second call succeeds

    with patch("app.services.email_service._send", side_effect=fail_then_succeed), \
         patch("app.services.email_service.asyncio.sleep", new_callable=AsyncMock):
        await send_completion_email("test@example.com", "https://example.com/bundle.zip", "My Book")

    assert call_count == 2  # Failed once, succeeded on retry


@pytest.mark.asyncio
async def test_send_completion_email_does_not_raise_on_double_failure():
    """Even if both attempts fail, send_completion_email() must not raise."""
    with patch("app.services.email_service._send", new_callable=AsyncMock, side_effect=ConnectionError("SMTP down")), \
         patch("app.services.email_service.asyncio.sleep", new_callable=AsyncMock):
        # Must not raise — job status is unaffected
        await send_completion_email("test@example.com", "https://example.com/bundle.zip", "My Book")
