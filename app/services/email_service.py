"""Email delivery service. Sends KDP bundle download link on job completion."""
from __future__ import annotations

import asyncio
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import aiosmtplib
from jinja2 import Environment, FileSystemLoader

from app.config import settings

logger = logging.getLogger(__name__)

RETRY_DELAY_SECONDS = 60
MAX_ATTEMPTS = 2

# Initialize Jinja2 environment for email templates
TEMPLATE_DIR = Path(__file__).parent.parent / "templates"
jinja_env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))


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
    # Prepare template context
    context = {
        "book_title": book_title,
        "download_url": download_url,
    }

    # Render templates
    plain_template = jinja_env.get_template("email/completion_plain.txt.j2")
    html_template = jinja_env.get_template("email/completion_html.html.j2")
    text_body = plain_template.render(context)
    html_body = html_template.render(context)

    # Create email message
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Your book '{book_title}' is ready for download!"
    msg["From"] = settings.smtp_user or "noreply@bookengine.io"
    msg["To"] = to_email

    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    # Send email
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
