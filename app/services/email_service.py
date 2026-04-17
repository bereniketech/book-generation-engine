"""Email delivery service. Sends KDP bundle download link on job completion."""
from __future__ import annotations

import asyncio
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import aiosmtplib

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
    <p><a href="{download_url}"
    style="background:#1a1a2e;color:#fff;padding:12px 24px;border-radius:8px;text-decoration:none;">
    Download KDP Bundle</a></p>
    <p>Link valid for 7 days. Bundle includes: manuscript.epub, manuscript.pdf, cover.jpg,
    cover-brief.txt, description.txt, metadata.json</p>
    </body></html>
    """
    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    smtp_host = settings.smtp_host or "localhost"
    smtp_port = settings.smtp_port

    await aiosmtplib.send(
        msg,
        hostname=smtp_host,
        port=smtp_port,
        username=settings.smtp_user or None,
        password=settings.smtp_password or None,
        start_tls=True,
    )
