"""Centralized job creation service - single source of truth for job creation logic.

This service consolidates all job creation logic (validation, DB insert, queue publish)
into a single place to enforce DRY principle and ensure consistency across all routes.
"""
from __future__ import annotations

import uuid
from typing import Optional

import aio_pika
from pydantic import ValidationError
from supabase import Client

from app.domain.validation_schemas import JobCreateRequest
from app.models.job import JobResponse
from app.queue.publisher import publish_job
from app.services import job_service


class JobCreateResult:
    """Result of a successful job creation."""

    def __init__(self, job_id: str, ws_url: str, status: str = "queued"):
        self.job_id = job_id
        self.ws_url = ws_url
        self.status = status

    def to_dict(self) -> dict:
        return {
            "job_id": self.job_id,
            "status": self.status,
            "ws_url": self.ws_url,
        }


def merge_template(template: dict, overrides: JobCreateRequest) -> JobCreateRequest:
    """Merge a template config with override values to produce a final JobCreateRequest.

    This is a pure function that combines template config with user overrides.
    Template config values are overridden by any explicit values in the overrides.

    Args:
        template: Template dict with a "config" key containing job config
        overrides: JobCreateRequest with override values

    Returns:
        A new JobCreateRequest with template values merged with overrides

    Raises:
        ValidationError: If the merged config fails validation
    """
    template_config = template.get("config", {})
    base = JobCreateRequest(**template_config)

    # Use model_copy with deep=True to properly handle nested models,
    # and pass the overrides as a model instance instead of dict to preserve types
    merged_dict = base.model_dump()
    override_dict = overrides.model_dump(exclude_unset=True)

    # Deep merge: override dict values into merged_dict
    merged_dict.update(override_dict)

    # Reconstruct as JobCreateRequest to ensure proper type validation
    return JobCreateRequest(**merged_dict)


async def create_job(
    request: JobCreateRequest,
    supabase: Client,
    channel: aio_pika.abc.AbstractChannel,
    email: Optional[str] = None,
) -> JobCreateResult:
    """Create a new job with full validation, DB insertion, and queue publishing.

    This is the single source of truth for job creation. All API routes should use this function.

    Args:
        request: Validated JobCreateRequest
        supabase: Supabase client
        channel: AMQP channel for publishing
        email: Optional notification email

    Returns:
        JobCreateResult with job_id and ws_url

    Raises:
        ValidationError: If the request fails validation (should not happen if request is already validated)
    """
    job_id = str(uuid.uuid4())
    config = request.model_dump()

    job_service.create_job(
        supabase=supabase,
        job_id=job_id,
        config=config,
        notification_email=email or request.notification_email,
    )

    await publish_job(channel=channel, job_id=job_id, config=config)

    return JobCreateResult(
        job_id=job_id,
        ws_url=f"/v1/ws/{job_id}",
    )


def validate_job_request(raw_data: dict) -> tuple[Optional[JobCreateRequest], Optional[list[str]]]:
    """Validate raw job data against JobCreateRequest schema.

    Returns a tuple of (validated_request, errors).
    If validation succeeds, returns (request, None).
    If validation fails, returns (None, error_list).

    This is useful for batch processing where you want to collect errors per row
    rather than failing fast.
    """
    try:
        request = JobCreateRequest(**raw_data)
        return request, None
    except ValidationError as exc:
        errors = [f"{e['loc'][0]}: {e['msg']}" for e in exc.errors()]
        return None, errors
