"""FastAPI dependency injection functions."""
from __future__ import annotations

from supabase import Client

from app.infrastructure.supabase_client import get_supabase_client


def get_supabase() -> Client:
    """Get Supabase client singleton.

    Using a dedicated dependency makes it trivial to override in tests:

    ```python
    from app.api.deps import get_supabase

    app.dependency_overrides[get_supabase] = lambda: mock_client
    ```
    """
    return get_supabase_client()
