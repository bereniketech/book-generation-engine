"""Unit tests for job creation service."""
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from pydantic import ValidationError

from app.domain.validation_schemas import JobCreateRequest
from app.services.job_creation_service import (
    create_job,
    merge_template,
    validate_job_request,
    JobCreateResult,
)


def make_valid_job_request() -> JobCreateRequest:
    """Create a valid JobCreateRequest for testing."""
    return JobCreateRequest(
        title="Test Book",
        topic="Testing concepts",
        mode="fiction",
        audience="Developers",
        tone="Casual",
        target_chapters=3,
        llm={"provider": "anthropic", "model": "claude-sonnet-4-6", "api_key": "test-key"},
        image={"provider": "dall-e-3", "api_key": "img-key"},
        notification_email="test@example.com",
    )


class TestMergeTemplate:
    """Tests for merge_template pure function."""

    def test_merge_template_overrides_specified_fields(self):
        """Template values are overridden by explicit overrides."""
        template = {
            "config": {
                "title": "Template Title",
                "topic": "Template Topic",
                "mode": "fiction",
                "audience": "Everyone",
                "tone": "Formal",
                "target_chapters": 12,
                "llm": {"provider": "anthropic", "model": "claude-opus", "api_key": "template-key"},
                "image": {"provider": "dall-e-3", "api_key": "template-img-key"},
            }
        }

        overrides = JobCreateRequest(
            title="Override Title",  # This should override template
            topic="Template Topic",  # Not in overrides, keep template
            mode="non_fiction",  # Override
            audience="Everyone",
            tone="Formal",
            target_chapters=8,  # Override
            llm={"provider": "openai", "model": "gpt-4", "api_key": "override-key"},
            image={"provider": "replicate-flux", "api_key": "override-img-key"},
        )

        result = merge_template(template, overrides)

        assert result.title == "Override Title"
        assert result.topic == "Template Topic"
        assert result.mode == "non_fiction"
        assert result.target_chapters == 8
        # Check the LLM provider from override
        assert result.llm.provider == "openai"
        assert result.image.provider == "replicate-flux"

    def test_merge_template_with_no_template_config(self):
        """Handles missing template config gracefully."""
        template = {}
        overrides = make_valid_job_request()

        # Should fail validation because template config is empty
        with pytest.raises(ValidationError):
            merge_template(template, overrides)

    def test_merge_template_preserves_unspecified_overrides(self):
        """Template values are used when overrides don't specify them."""
        template = {
            "config": {
                "title": "Template Title",
                "topic": "Template Topic",
                "mode": "fiction",
                "audience": "Everyone",
                "tone": "Formal",
                "target_chapters": 12,
                "llm": {"provider": "anthropic", "model": "claude-opus", "api_key": "template-key"},
                "image": {"provider": "dall-e-3", "api_key": "template-img-key"},
            }
        }

        overrides = JobCreateRequest(
            title="Template Title",
            topic="Template Topic",
            mode="fiction",
            audience="Everyone",
            tone="Formal",
            target_chapters=12,
            llm={"provider": "anthropic", "model": "claude-opus", "api_key": "template-key"},
            image={"provider": "dall-e-3", "api_key": "template-img-key"},
        )

        result = merge_template(template, overrides)

        assert result.title == "Template Title"
        assert result.topic == "Template Topic"
        assert result.mode == "fiction"


class TestValidateJobRequest:
    """Tests for validate_job_request function."""

    def test_validate_job_request_valid_data(self):
        """Valid data passes validation."""
        valid_data = {
            "title": "Test Book",
            "topic": "Testing concepts",
            "mode": "fiction",
            "audience": "Developers",
            "tone": "Casual",
            "target_chapters": 3,
            "llm": {"provider": "anthropic", "model": "claude-sonnet-4-6", "api_key": "test-key"},
            "image": {"provider": "dall-e-3", "api_key": "img-key"},
            "notification_email": "test@example.com",
        }

        request, errors = validate_job_request(valid_data)

        assert request is not None
        assert errors is None
        assert request.title == "Test Book"

    def test_validate_job_request_missing_required_field(self):
        """Missing required field produces errors."""
        invalid_data = {
            "title": "Test Book",
            # missing 'topic'
            "mode": "fiction",
            "audience": "Developers",
            "tone": "Casual",
            "target_chapters": 3,
            "llm": {"provider": "anthropic", "model": "claude-sonnet-4-6", "api_key": "test-key"},
            "image": {"provider": "dall-e-3", "api_key": "img-key"},
        }

        request, errors = validate_job_request(invalid_data)

        assert request is None
        assert errors is not None
        assert len(errors) > 0
        assert any("topic" in error for error in errors)

    def test_validate_job_request_invalid_email(self):
        """Invalid email format produces errors."""
        invalid_data = {
            "title": "Test Book",
            "topic": "Testing concepts",
            "mode": "fiction",
            "audience": "Developers",
            "tone": "Casual",
            "target_chapters": 3,
            "llm": {"provider": "anthropic", "model": "claude-sonnet-4-6", "api_key": "test-key"},
            "image": {"provider": "dall-e-3", "api_key": "img-key"},
            "notification_email": "not-an-email",
        }

        request, errors = validate_job_request(invalid_data)

        assert request is None
        assert errors is not None

    def test_validate_job_request_invalid_llm_provider(self):
        """Invalid LLM provider produces errors."""
        invalid_data = {
            "title": "Test Book",
            "topic": "Testing concepts",
            "mode": "fiction",
            "audience": "Developers",
            "tone": "Casual",
            "target_chapters": 3,
            "llm": {"provider": "invalid-provider", "model": "model", "api_key": "key"},
            "image": {"provider": "dall-e-3", "api_key": "img-key"},
        }

        request, errors = validate_job_request(invalid_data)

        assert request is None
        assert errors is not None


class TestCreateJob:
    """Tests for create_job async function."""

    @pytest.mark.asyncio
    async def test_create_job_success(self):
        """Successfully creates a job and returns result."""
        request = make_valid_job_request()
        mock_supabase = MagicMock()
        mock_channel = AsyncMock()

        with patch("app.services.job_creation_service.job_service.create_job") as mock_create, \
             patch("app.services.job_creation_service.publish_job", new_callable=AsyncMock) as mock_publish, \
             patch("app.services.job_creation_service.uuid.uuid4", return_value="test-job-id"):

            result = await create_job(
                request=request,
                supabase=mock_supabase,
                channel=mock_channel,
                email="custom@example.com",
            )

        assert isinstance(result, JobCreateResult)
        assert result.job_id == "test-job-id"
        assert result.status == "queued"
        assert "/v1/ws/test-job-id" in result.ws_url

        # Verify job_service.create_job was called with correct args
        mock_create.assert_called_once()
        call_kwargs = mock_create.call_args[1]
        assert call_kwargs["job_id"] == "test-job-id"
        assert call_kwargs["notification_email"] == "custom@example.com"

        # Verify publish_job was called
        mock_publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_job_uses_request_email_if_no_override(self):
        """Uses email from request if no email parameter provided."""
        request = make_valid_job_request()
        mock_supabase = MagicMock()
        mock_channel = AsyncMock()

        with patch("app.services.job_creation_service.job_service.create_job") as mock_create, \
             patch("app.services.job_creation_service.publish_job", new_callable=AsyncMock), \
             patch("app.services.job_creation_service.uuid.uuid4", return_value="test-job-id"):

            result = await create_job(
                request=request,
                supabase=mock_supabase,
                channel=mock_channel,
                email=None,
            )

        call_kwargs = mock_create.call_args[1]
        assert call_kwargs["notification_email"] == "test@example.com"

    @pytest.mark.asyncio
    async def test_create_job_returns_correct_ws_url(self):
        """Returns correct WebSocket URL."""
        request = make_valid_job_request()
        mock_supabase = MagicMock()
        mock_channel = AsyncMock()

        with patch("app.services.job_creation_service.job_service.create_job"), \
             patch("app.services.job_creation_service.publish_job", new_callable=AsyncMock), \
             patch("app.services.job_creation_service.uuid.uuid4", return_value="abc123"):

            result = await create_job(
                request=request,
                supabase=mock_supabase,
                channel=mock_channel,
            )

        assert result.ws_url == "/v1/ws/abc123"


class TestJobCreateResult:
    """Tests for JobCreateResult model."""

    def test_job_create_result_to_dict(self):
        """to_dict converts result to dictionary."""
        result = JobCreateResult(
            job_id="job-123",
            ws_url="/v1/ws/job-123",
            status="queued",
        )

        d = result.to_dict()

        assert d["job_id"] == "job-123"
        assert d["ws_url"] == "/v1/ws/job-123"
        assert d["status"] == "queued"

    def test_job_create_result_default_status(self):
        """Default status is 'queued'."""
        result = JobCreateResult(
            job_id="job-123",
            ws_url="/v1/ws/job-123",
        )

        assert result.status == "queued"
