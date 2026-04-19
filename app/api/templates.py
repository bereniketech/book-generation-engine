"""Job config template endpoints."""
from __future__ import annotations

import os
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException
from supabase import create_client

from app.core.logging import get_logger

log = get_logger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")

router = APIRouter(prefix="/templates", tags=["templates"])


def _client():
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


class CreateTemplateRequest(BaseModel):
    name: str
    config: dict


@router.get("")
async def list_templates():
    result = _client().table("job_templates").select("id,name,config,created_at").order("created_at", desc=True).execute()
    return {"templates": result.data}


@router.post("", status_code=201)
async def create_template(body: CreateTemplateRequest):
    try:
        result = _client().table("job_templates").insert({
            "name": body.name,
            "config": body.config,
        }).execute()
        return result.data[0]
    except Exception as exc:
        if "unique" in str(exc).lower() or "duplicate" in str(exc).lower():
            raise HTTPException(
                status_code=409,
                detail={"error": "Template name already exists", "code": "TEMPLATE_EXISTS"},
            )
        raise HTTPException(status_code=500, detail={"error": str(exc), "code": "INTERNAL_ERROR"})
