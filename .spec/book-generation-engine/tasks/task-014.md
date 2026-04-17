---
task: 014
feature: book-generation-engine
status: pending
model: haiku
supervisor: software-cto
agent: software-developer-expert
depends_on: [013]
---

# Task 014: Email Delivery Service

## Skills
- .kit/skills/languages/python-patterns/SKILL.md
- .kit/rules/python/patterns.md

## Agents
- @software-developer-expert

## Commands
- /task-handoff

> Load the skills, agents, and commands listed above before reading anything else.

---

## Objective

Implement `app/services/email_service.py` that sends the KDP bundle download link to the author on job completion, retrying once on failure after 60 seconds. Job status is unaffected by email outcome.

---

## Files

### Create
| File | Purpose |
|------|---------|
| `app/services/email_service.py` | SMTP email delivery with one retry |
| `tests/unit/test_email_service.py` | Unit tests: success, failure+retry, second-failure |

---

## Dependencies

```bash
# aiosmtplib already in pyproject.toml.
# Env vars already in .env.example: SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, FROM_EMAIL
```

---

## Code Templates

### `app/services/email_service.py` (create this file exactly)
```python
"""Email delivery service. Sends KDP bundle download link on job completion."""
from __future__ import annotations

import asyncio
import logging

import aiosmtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.config import settings

logger = logging.getLogger(__name__)

RETRY_DELAY_SECONDS = 60
MAX_ATTEMPTS = 2


async def send_completion_email(
    to_email: str,
    download_url: str,
    book_title: str,
) -> None:
    """Send KDP bundle download email. Retries once on failure. Never raises."""
    for attempt in range(MAX_ATTEMPTS):
        try:
            await _send(to_email, download_url, book_title)
            logger.info("Completion email sent to %s for book '%s'", to_email, book_title)
            return
        except Exception as exc:
            logger.error(
                "Email delivery failed (attempt %d/%d): %s",
                attempt + 1,
                MAX_ATTEMPTS,
                exc,
            )
            if attempt < MAX_ATTEMPTS - 1:
                logger.info("Retrying email in %ds...", RETRY_DELAY_SECONDS)
                await asyncio.sleep(RETRY_DELAY_SECONDS)
    logger.error("Email delivery permanently failed for %s — job status unaffected.", to_email)


async def _send(to_email: str, download_url: str, book_title: str) -> None:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Your book '{book_title}' is ready for download!"
    msg["From"] = settings.smtp_user or "noreply@bookengine.io"
    msg["To"] = to_email

    text_body = (
        f"Your KDP bundle for '{book_title}' is ready.\n\n"
        f"Download link (valid for 7 days):\n{download_url}\n\n"
        "The bundle contains: manuscript.epub, manuscript.pdf, cover.jpg, "
        "cover-brief.txt, description.txt, metadata.json\n"
    )
    html_body = f"""
    <html><body>
    <h2>Your book is ready!</h2>
    <p>Your KDP bundle for <strong>{book_title}</strong> has been generated.</p>
    <p><a href="{download_url}" style="background:#1a1a2e;color:#fff;padding:12px 24px;border-radius:8px;text-decoration:none;">
    Download KDP Bundle</a></p>
    <p>Link valid for 7 days. Bundle includes: manuscript.epub, manuscript.pdf, cover.jpg, 
    cover-brief.txt, description.txt, metadata.json</p>
    </body></html>
    """
    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    smtp_host = settings.smtp_host or "localhost"
    smtp_port = int(getattr(settings, "smtp_port", 587))

    await aiosmtplib.send(
        msg,
        hostname=smtp_host,
        port=smtp_port,
        username=getattr(settings, "smtp_user", None),
        password=getattr(settings, "smtp_password", None),
        start_tls=True,
    )
```

### `tests/unit/test_email_service.py` (create this file exactly)
```python
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
```

---

## Codebase Context

### Key Patterns in Use
- **`send_completion_email` never raises:** All exceptions caught internally. Caller does not need a try/except.
- **Retry once after 60s:** `MAX_ATTEMPTS = 2`. Sleep only between attempts, not after last failure.
- **SMTP via `aiosmtplib`:** Async SMTP client. `start_tls=True` for port 587.
- **Config from `settings`:** `settings.smtp_host`, `settings.smtp_port`, `settings.smtp_user`, `settings.smtp_password`. All optional — default to `"localhost"` / `587` if absent.

### Architecture Decisions Affecting This Task
- Requirement 8.2: "IF email delivery fails THEN the system SHALL log the error and retry once after 60 seconds; the job status SHALL remain `complete` regardless of email outcome."
- The runner (task-011) calls `send_completion_email()` after setting job status to `complete`. It does not await the email before returning.

---

## Handoff from Previous Task

**Files changed by previous task:** `app/api/chapters.py`, `app/services/chapter_service.py`, `app/services/storage_service.py`, `app/models/chapter.py`, `app/main.py`.
**Decisions made:** 409 for locked chapters. 202 Accepted for regenerate. 400 for non-complete export.
**Context for this task:** All API routes done. Now add email delivery.
**Open questions left:** _(none)_

---

## Implementation Steps

1. Edit `app/config.py` to add `smtp_host: str = ""`, `smtp_port: int = 587`, `smtp_user: str = ""`, `smtp_password: str = ""` fields to the `Settings` class.
2. Create `app/services/email_service.py` — paste template exactly.
3. Create `tests/unit/test_email_service.py` — paste template exactly.
4. Run: `pytest tests/unit/test_email_service.py -v` — verify all 3 tests pass.
5. Run: `ruff check app/services/email_service.py` — verify zero lint errors.

---

## Decision Rules

| Scenario | Action |
|----------|--------|
| `_send()` raises on attempt 1 | Log error, sleep 60s, retry `_send()` on attempt 2 |
| `_send()` raises on attempt 2 | Log error "permanently failed", return without raising |
| `to_email` is `None` | Caller (runner) checks `config.notification_email` before calling — never call with `None` |

---

## Acceptance Criteria

- [ ] WHEN `send_completion_email()` is called and SMTP succeeds THEN email is sent once
- [ ] WHEN first SMTP call fails THEN retry is made after sleeping 60s
- [ ] WHEN both SMTP calls fail THEN no exception is raised by `send_completion_email()`
- [ ] WHEN `pytest tests/unit/test_email_service.py` runs THEN all 3 tests pass

---

## Handoff to Next Task

**Files changed:** _(fill via /task-handoff)_
**Decisions made:** _(fill via /task-handoff)_
**Context for next task:** _(fill via /task-handoff)_
**Open questions:** _(fill via /task-handoff)_

Status: COMPLETE
Completed: 2026-04-17T00:00:00Z
