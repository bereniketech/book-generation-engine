"""Job config template endpoints."""
from __future__ import annotations

from pydantic import BaseModel
from fastapi import APIRouter

from app.core.logging import get_logger
from app.infrastructure.http_exceptions import ConflictError, InternalError
from app.infrastructure.security import redact_sensitive_fields
from app.infrastructure.supabase_client import get_supabase_client

log = get_logger(__name__)

router = APIRouter(prefix="/templates", tags=["templates"])


class CreateTemplateRequest(BaseModel):
    name: str
    config: dict


@router.get("")
async def list_templates():
    result = get_supabase_client().table("job_templates").select("id,name,config,created_at").order("created_at", desc=True).execute()
    return {"templates": [redact_sensitive_fields(t) for t in result.data]}


@router.post("", status_code=201)
async def create_template(body: CreateTemplateRequest):
    try:
        result = get_supabase_client().table("job_templates").insert({
            "name": body.name,
            "config": body.config,
        }).execute()
        return redact_sensitive_fields(result.data[0])
    except Exception as exc:
        if "unique" in str(exc).lower() or "duplicate" in str(exc).lower():
            raise ConflictError("Template name already exists", code="TEMPLATE_EXISTS")
        raise InternalError(str(exc))
