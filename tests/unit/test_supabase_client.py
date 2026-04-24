"""Unit tests for centralized Supabase client factory."""
from __future__ import annotations

import importlib
import sys
from unittest.mock import MagicMock, patch


def _clear_lru_cache():
    """Clear the lru_cache on get_supabase_client so tests are isolated."""
    # Re-import after clearing to get a fresh function
    if "app.infrastructure.supabase_client" in sys.modules:
        mod = sys.modules["app.infrastructure.supabase_client"]
        mod.get_supabase_client.cache_clear()


def test_get_supabase_client_returns_client():
    """WHEN env vars are set THEN get_supabase_client SHALL return a client."""
    _clear_lru_cache()
    mock_client = MagicMock()
    with patch.dict("os.environ", {"SUPABASE_URL": "https://test.supabase.co", "SUPABASE_SERVICE_KEY": "test-key"}):
        with patch("app.infrastructure.supabase_client.create_client", return_value=mock_client) as mock_create:
            from app.infrastructure.supabase_client import get_supabase_client
            _clear_lru_cache()
            result = get_supabase_client()
            mock_create.assert_called_once_with("https://test.supabase.co", "test-key")
            assert result is mock_client


def test_get_supabase_client_returns_same_instance():
    """WHEN get_supabase_client is called twice THEN it SHALL return the same instance (lru_cache)."""
    _clear_lru_cache()
    mock_client = MagicMock()
    with patch.dict("os.environ", {"SUPABASE_URL": "https://test.supabase.co", "SUPABASE_SERVICE_KEY": "test-key"}):
        with patch("app.infrastructure.supabase_client.create_client", return_value=mock_client) as mock_create:
            from app.infrastructure.supabase_client import get_supabase_client
            _clear_lru_cache()
            first = get_supabase_client()
            second = get_supabase_client()
            assert first is second
            # create_client called only once due to lru_cache
            assert mock_create.call_count == 1


def test_get_supabase_client_raises_when_url_missing():
    """IF SUPABASE_URL is not set THEN get_supabase_client SHALL raise RuntimeError."""
    _clear_lru_cache()
    import os
    env = {k: v for k, v in os.environ.items() if k not in ("SUPABASE_URL", "SUPABASE_SERVICE_KEY")}
    env["SUPABASE_SERVICE_KEY"] = "test-key"
    with patch.dict("os.environ", env, clear=True):
        from app.infrastructure.supabase_client import get_supabase_client
        _clear_lru_cache()
        try:
            get_supabase_client()
            assert False, "Should have raised RuntimeError"
        except RuntimeError as exc:
            assert "Supabase credentials not configured" in str(exc)


def test_get_supabase_client_raises_when_key_missing():
    """IF SUPABASE_SERVICE_KEY is not set THEN get_supabase_client SHALL raise RuntimeError."""
    _clear_lru_cache()
    import os
    env = {k: v for k, v in os.environ.items() if k not in ("SUPABASE_URL", "SUPABASE_SERVICE_KEY")}
    env["SUPABASE_URL"] = "https://test.supabase.co"
    with patch.dict("os.environ", env, clear=True):
        from app.infrastructure.supabase_client import get_supabase_client
        _clear_lru_cache()
        try:
            get_supabase_client()
            assert False, "Should have raised RuntimeError"
        except RuntimeError as exc:
            assert "Supabase credentials not configured" in str(exc)


def test_get_supabase_client_raises_when_both_missing():
    """IF both SUPABASE_URL and SUPABASE_SERVICE_KEY are absent THEN SHALL raise RuntimeError."""
    _clear_lru_cache()
    import os
    env = {k: v for k, v in os.environ.items() if k not in ("SUPABASE_URL", "SUPABASE_SERVICE_KEY")}
    with patch.dict("os.environ", env, clear=True):
        from app.infrastructure.supabase_client import get_supabase_client
        _clear_lru_cache()
        try:
            get_supabase_client()
            assert False, "Should have raised RuntimeError"
        except RuntimeError as exc:
            assert "Supabase credentials not configured" in str(exc)
