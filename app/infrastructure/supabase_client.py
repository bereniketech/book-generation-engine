"""Centralized Supabase client management."""
from __future__ import annotations

import os
from functools import lru_cache

from supabase import Client, create_client


@lru_cache(maxsize=1)
def get_supabase_client() -> Client:
    """Get singleton Supabase client instance.

    Uses lru_cache for connection pooling and reuse across the application.
    Raises RuntimeError if credentials are not configured via environment variables.
    """
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY")

    if not url or not key:
        raise RuntimeError("Supabase credentials not configured")

    return create_client(url, key)
