"""Storage service for signed URL generation (app-side)."""
from __future__ import annotations

from supabase import Client

BUCKET = "book-artifacts"
SIGNED_URL_EXPIRY = 604800  # 7 days


def get_signed_url(supabase: Client, storage_path: str) -> str:
    response = supabase.storage.from_(BUCKET).create_signed_url(storage_path, SIGNED_URL_EXPIRY)
    return response["signedURL"]
