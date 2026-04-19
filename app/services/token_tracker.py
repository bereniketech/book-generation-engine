"""LLM token usage tracking — async insert and query."""
from __future__ import annotations

import os
from supabase import create_client, Client

from app.core.logging import get_logger

log = get_logger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")


def _get_client() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


async def record_usage(
    job_id: str,
    stage: str,
    provider: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
) -> None:
    """Insert one llm_usage row. Fire-and-forget — does not raise on failure."""
    try:
        client = _get_client()
        client.table("llm_usage").insert({
            "job_id": job_id,
            "stage": stage,
            "provider": provider,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        }).execute()
        log.debug(
            "token_usage.recorded",
            job_id=job_id,
            stage=stage,
            provider=provider,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
    except Exception as exc:
        try:
            log.error("token_usage.record_failed", job_id=job_id, error=str(exc))
        except ValueError:
            pass


def get_job_usage(job_id: str) -> dict:
    """Return total and per-stage token usage for a job."""
    client = _get_client()
    rows = (
        client.table("llm_usage")
        .select("stage,provider,model,input_tokens,output_tokens")
        .eq("job_id", job_id)
        .execute()
        .data
    )
    total_in = sum(r["input_tokens"] for r in rows)
    total_out = sum(r["output_tokens"] for r in rows)
    return {
        "job_id": job_id,
        "total": {"input_tokens": total_in, "output_tokens": total_out},
        "by_stage": rows,
    }


def get_aggregate_usage() -> dict:
    """Return aggregate token usage grouped by provider and date."""
    client = _get_client()
    rows = (
        client.table("llm_usage")
        .select("provider,model,input_tokens,output_tokens,created_at")
        .order("created_at", desc=True)
        .limit(1000)
        .execute()
        .data
    )
    from collections import defaultdict
    grouped: dict[str, dict] = defaultdict(lambda: {"input_tokens": 0, "output_tokens": 0})
    for r in rows:
        date = r["created_at"][:10]
        key = f"{r['provider']}|{date}"
        grouped[key]["provider"] = r["provider"]
        grouped[key]["date"] = date
        grouped[key]["input_tokens"] += r["input_tokens"]
        grouped[key]["output_tokens"] += r["output_tokens"]
    return {"by_provider": list(grouped.values())}
