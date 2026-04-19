"""Admin API endpoints — token aggregates and DLQ inspection."""
from __future__ import annotations

import os
from fastapi import APIRouter, Header, HTTPException

from app.services.token_tracker import get_aggregate_usage
from worker.dlq import get_dlq_status, retry_dlq_messages

ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "")

router = APIRouter(prefix="/admin", tags=["admin"])


def _require_admin(x_admin_key: str | None) -> None:
    if not ADMIN_API_KEY or x_admin_key != ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail={"error": "Forbidden", "code": "FORBIDDEN"})


@router.get("/tokens")
async def admin_token_aggregate(x_admin_key: str | None = Header(default=None)):
    _require_admin(x_admin_key)
    return get_aggregate_usage()


@router.get("/dlq")
async def admin_dlq_list(x_admin_key: str | None = Header(default=None)):
    _require_admin(x_admin_key)
    return get_dlq_status()


@router.post("/dlq/retry")
async def admin_dlq_retry(x_admin_key: str | None = Header(default=None)):
    _require_admin(x_admin_key)
    requeued = await retry_dlq_messages()
    return {"requeued": requeued}
