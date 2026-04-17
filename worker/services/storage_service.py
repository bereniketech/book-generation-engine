"""Supabase Storage upload helper for worker processes."""
from __future__ import annotations

import logging

from supabase import Client

logger = logging.getLogger(__name__)

BUCKET = "book-artifacts"


def upload_bytes(
    supabase: Client, job_id: str, filename: str, data: bytes, content_type: str
) -> str:
    """Upload bytes to Supabase Storage. Returns storage path."""
    path = f"{job_id}/{filename}"
    supabase.storage.from_(BUCKET).upload(
        path=path,
        file=data,
        file_options={"content-type": content_type, "upsert": "true"},
    )
    logger.info("Uploaded %s (%d bytes) for job %s", filename, len(data), job_id)
    return path


def get_signed_url(supabase: Client, path: str, expires_in: int = 604800) -> str:
    """Return a signed URL valid for expires_in seconds (default 7 days)."""
    response = supabase.storage.from_(BUCKET).create_signed_url(path, expires_in)
    return response["signedURL"]
