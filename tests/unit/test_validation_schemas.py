"""Unit tests for app.domain.validation_schemas.

Covers:
- JobCreateRequest field constraints (min/max, required, optional)
- LLMProviderConfig constraints
- ImageProviderConfig constraints
- Boundary conditions (exact min/max values)
- Invalid provider enum values
- Email validation for notification_email

Constraint reference (must match frontend/lib/validation.ts):
  title            : min 1, max 500
  topic            : min 1, max 2000
  mode             : fiction | non_fiction
  audience         : min 1, max 500
  tone             : min 1, max 200
  target_chapters  : int, min 3, max 50
  llm.model        : min 1, max 200
  llm.api_key      : min 1, max 500
  image.api_key    : min 1, max 500
  notification_email: optional valid email
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.domain.validation_schemas import (
    ImageProviderConfig,
    JobCreateRequest,
    LLMProviderConfig,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _valid_llm() -> dict:
    return {"provider": "anthropic", "model": "claude-sonnet-4-6", "api_key": "sk-test-key"}


def _valid_image() -> dict:
    return {"provider": "dall-e-3", "api_key": "sk-image-key"}


def _valid_payload(**overrides) -> dict:
    base = {
        "title": "Test Book",
        "topic": "A test topic",
        "mode": "fiction",
        "audience": "Adults",
        "tone": "Formal",
        "target_chapters": 12,
        "llm": _valid_llm(),
        "image": _valid_image(),
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# LLMProviderConfig
# ---------------------------------------------------------------------------

def test_llm_config_valid():
    """WHEN a valid LLM config is supplied THEN it SHALL parse successfully."""
    cfg = LLMProviderConfig(**_valid_llm())
    assert cfg.provider == "anthropic"
    assert cfg.model == "claude-sonnet-4-6"


def test_llm_config_invalid_provider():
    """WHEN an unsupported LLM provider is supplied THEN ValidationError SHALL be raised."""
    with pytest.raises(ValidationError):
        LLMProviderConfig(provider="unsupported", model="gpt-4", api_key="key")


def test_llm_config_all_valid_providers():
    """WHEN each valid LLM provider is used THEN it SHALL parse without error."""
    valid_providers = ["anthropic", "openai", "google", "ollama", "openai-compatible"]
    for provider in valid_providers:
        cfg = LLMProviderConfig(provider=provider, model="m", api_key="k")
        assert cfg.provider == provider


def test_llm_config_model_empty_string_raises():
    """WHEN model is an empty string THEN ValidationError SHALL be raised."""
    with pytest.raises(ValidationError):
        LLMProviderConfig(provider="anthropic", model="", api_key="key")


def test_llm_config_model_max_length_boundary():
    """WHEN model is exactly 200 characters THEN it SHALL be accepted."""
    cfg = LLMProviderConfig(provider="anthropic", model="a" * 200, api_key="key")
    assert len(cfg.model) == 200


def test_llm_config_model_exceeds_max_length():
    """WHEN model exceeds 200 characters THEN ValidationError SHALL be raised."""
    with pytest.raises(ValidationError):
        LLMProviderConfig(provider="anthropic", model="a" * 201, api_key="key")


def test_llm_config_api_key_max_length_boundary():
    """WHEN api_key is exactly 500 characters THEN it SHALL be accepted."""
    cfg = LLMProviderConfig(provider="anthropic", model="m", api_key="k" * 500)
    assert len(cfg.api_key) == 500


def test_llm_config_api_key_exceeds_max_length():
    """WHEN api_key exceeds 500 characters THEN ValidationError SHALL be raised."""
    with pytest.raises(ValidationError):
        LLMProviderConfig(provider="anthropic", model="m", api_key="k" * 501)


def test_llm_config_base_url_optional():
    """WHEN base_url is omitted THEN it SHALL default to None."""
    cfg = LLMProviderConfig(provider="anthropic", model="m", api_key="k")
    assert cfg.base_url is None


def test_llm_config_base_url_provided():
    """WHEN a valid base_url is supplied THEN it SHALL be stored."""
    cfg = LLMProviderConfig(
        provider="openai-compatible",
        model="local-model",
        api_key="k",
        base_url="http://localhost:11434",
    )
    assert cfg.base_url == "http://localhost:11434"


# ---------------------------------------------------------------------------
# ImageProviderConfig
# ---------------------------------------------------------------------------

def test_image_config_valid_dalle():
    """WHEN provider is 'dall-e-3' THEN it SHALL parse successfully."""
    cfg = ImageProviderConfig(provider="dall-e-3", api_key="sk-img")
    assert cfg.provider == "dall-e-3"


def test_image_config_valid_replicate():
    """WHEN provider is 'replicate-flux' THEN it SHALL parse successfully."""
    cfg = ImageProviderConfig(provider="replicate-flux", api_key="r-key")
    assert cfg.provider == "replicate-flux"


def test_image_config_invalid_provider():
    """WHEN an unsupported image provider is supplied THEN ValidationError SHALL be raised."""
    with pytest.raises(ValidationError):
        ImageProviderConfig(provider="midjourney", api_key="key")


def test_image_config_api_key_empty_raises():
    """WHEN api_key is empty THEN ValidationError SHALL be raised."""
    with pytest.raises(ValidationError):
        ImageProviderConfig(provider="dall-e-3", api_key="")


def test_image_config_api_key_max_boundary():
    """WHEN api_key is exactly 500 characters THEN it SHALL be accepted."""
    cfg = ImageProviderConfig(provider="dall-e-3", api_key="k" * 500)
    assert len(cfg.api_key) == 500


def test_image_config_api_key_exceeds_max():
    """WHEN api_key exceeds 500 characters THEN ValidationError SHALL be raised."""
    with pytest.raises(ValidationError):
        ImageProviderConfig(provider="dall-e-3", api_key="k" * 501)


# ---------------------------------------------------------------------------
# JobCreateRequest — title
# ---------------------------------------------------------------------------

def test_job_create_title_required():
    """WHEN title is empty THEN ValidationError SHALL be raised."""
    with pytest.raises(ValidationError):
        JobCreateRequest(**_valid_payload(title=""))


def test_job_create_title_max_boundary():
    """WHEN title is exactly 500 characters THEN it SHALL be accepted."""
    job = JobCreateRequest(**_valid_payload(title="t" * 500))
    assert len(job.title) == 500


def test_job_create_title_exceeds_max():
    """WHEN title exceeds 500 characters THEN ValidationError SHALL be raised."""
    with pytest.raises(ValidationError):
        JobCreateRequest(**_valid_payload(title="t" * 501))


# ---------------------------------------------------------------------------
# JobCreateRequest — topic
# ---------------------------------------------------------------------------

def test_job_create_topic_required():
    """WHEN topic is empty THEN ValidationError SHALL be raised."""
    with pytest.raises(ValidationError):
        JobCreateRequest(**_valid_payload(topic=""))


def test_job_create_topic_max_boundary():
    """WHEN topic is exactly 2000 characters THEN it SHALL be accepted."""
    job = JobCreateRequest(**_valid_payload(topic="t" * 2000))
    assert len(job.topic) == 2000


def test_job_create_topic_exceeds_max():
    """WHEN topic exceeds 2000 characters THEN ValidationError SHALL be raised."""
    with pytest.raises(ValidationError):
        JobCreateRequest(**_valid_payload(topic="t" * 2001))


# ---------------------------------------------------------------------------
# JobCreateRequest — audience
# ---------------------------------------------------------------------------

def test_job_create_audience_required():
    """WHEN audience is empty THEN ValidationError SHALL be raised."""
    with pytest.raises(ValidationError):
        JobCreateRequest(**_valid_payload(audience=""))


def test_job_create_audience_max_boundary():
    """WHEN audience is exactly 500 characters THEN it SHALL be accepted."""
    job = JobCreateRequest(**_valid_payload(audience="a" * 500))
    assert len(job.audience) == 500


def test_job_create_audience_exceeds_max():
    """WHEN audience exceeds 500 characters THEN ValidationError SHALL be raised."""
    with pytest.raises(ValidationError):
        JobCreateRequest(**_valid_payload(audience="a" * 501))


# ---------------------------------------------------------------------------
# JobCreateRequest — tone
# ---------------------------------------------------------------------------

def test_job_create_tone_required():
    """WHEN tone is empty THEN ValidationError SHALL be raised."""
    with pytest.raises(ValidationError):
        JobCreateRequest(**_valid_payload(tone=""))


def test_job_create_tone_max_boundary():
    """WHEN tone is exactly 200 characters THEN it SHALL be accepted."""
    job = JobCreateRequest(**_valid_payload(tone="t" * 200))
    assert len(job.tone) == 200


def test_job_create_tone_exceeds_max():
    """WHEN tone exceeds 200 characters THEN ValidationError SHALL be raised."""
    with pytest.raises(ValidationError):
        JobCreateRequest(**_valid_payload(tone="t" * 201))


# ---------------------------------------------------------------------------
# JobCreateRequest — target_chapters
# ---------------------------------------------------------------------------

def test_job_create_target_chapters_min_boundary():
    """WHEN target_chapters is exactly 3 THEN it SHALL be accepted."""
    job = JobCreateRequest(**_valid_payload(target_chapters=3))
    assert job.target_chapters == 3


def test_job_create_target_chapters_below_min():
    """WHEN target_chapters is 2 THEN ValidationError SHALL be raised."""
    with pytest.raises(ValidationError):
        JobCreateRequest(**_valid_payload(target_chapters=2))


def test_job_create_target_chapters_max_boundary():
    """WHEN target_chapters is exactly 50 THEN it SHALL be accepted."""
    job = JobCreateRequest(**_valid_payload(target_chapters=50))
    assert job.target_chapters == 50


def test_job_create_target_chapters_exceeds_max():
    """WHEN target_chapters is 51 THEN ValidationError SHALL be raised."""
    with pytest.raises(ValidationError):
        JobCreateRequest(**_valid_payload(target_chapters=51))


def test_job_create_target_chapters_default():
    """WHEN target_chapters is omitted THEN it SHALL default to 12."""
    payload = _valid_payload()
    del payload["target_chapters"]
    job = JobCreateRequest(**payload)
    assert job.target_chapters == 12


# ---------------------------------------------------------------------------
# JobCreateRequest — mode
# ---------------------------------------------------------------------------

def test_job_create_mode_fiction():
    """WHEN mode is 'fiction' THEN it SHALL be accepted."""
    job = JobCreateRequest(**_valid_payload(mode="fiction"))
    assert job.mode == "fiction"


def test_job_create_mode_non_fiction():
    """WHEN mode is 'non_fiction' THEN it SHALL be accepted."""
    job = JobCreateRequest(**_valid_payload(mode="non_fiction"))
    assert job.mode == "non_fiction"


def test_job_create_mode_invalid():
    """WHEN mode is an invalid value THEN ValidationError SHALL be raised."""
    with pytest.raises(ValidationError):
        JobCreateRequest(**_valid_payload(mode="biography"))


# ---------------------------------------------------------------------------
# JobCreateRequest — notification_email
# ---------------------------------------------------------------------------

def test_job_create_notification_email_optional():
    """WHEN notification_email is omitted THEN it SHALL default to None."""
    job = JobCreateRequest(**_valid_payload())
    assert job.notification_email is None


def test_job_create_notification_email_valid():
    """WHEN a valid email is supplied THEN it SHALL be stored."""
    job = JobCreateRequest(**_valid_payload(notification_email="user@example.com"))
    assert job.notification_email == "user@example.com"


def test_job_create_notification_email_invalid():
    """WHEN an invalid email string is supplied THEN ValidationError SHALL be raised."""
    with pytest.raises(ValidationError):
        JobCreateRequest(**_valid_payload(notification_email="not-an-email"))


# ---------------------------------------------------------------------------
# Constraint parity: verify frontend limits match backend
# ---------------------------------------------------------------------------

CONSTRAINT_PARITY = [
    ("title_max", 500),
    ("topic_max", 2000),
    ("audience_max", 500),
    ("tone_max", 200),
    ("target_chapters_min", 3),
    ("target_chapters_max", 50),
    ("llm_model_max", 200),
    ("llm_api_key_max", 500),
    ("image_api_key_max", 500),
]


def test_constraint_parity_title_max():
    """Backend title max SHALL be 500 to match Zod schema."""
    job = JobCreateRequest(**_valid_payload(title="x" * 500))
    assert len(job.title) == 500
    with pytest.raises(ValidationError):
        JobCreateRequest(**_valid_payload(title="x" * 501))


def test_constraint_parity_topic_max():
    """Backend topic max SHALL be 2000 to match Zod schema."""
    job = JobCreateRequest(**_valid_payload(topic="x" * 2000))
    assert len(job.topic) == 2000
    with pytest.raises(ValidationError):
        JobCreateRequest(**_valid_payload(topic="x" * 2001))


def test_constraint_parity_audience_max():
    """Backend audience max SHALL be 500 to match Zod schema."""
    job = JobCreateRequest(**_valid_payload(audience="x" * 500))
    assert len(job.audience) == 500
    with pytest.raises(ValidationError):
        JobCreateRequest(**_valid_payload(audience="x" * 501))


def test_constraint_parity_tone_max():
    """Backend tone max SHALL be 200 to match Zod schema."""
    job = JobCreateRequest(**_valid_payload(tone="x" * 200))
    assert len(job.tone) == 200
    with pytest.raises(ValidationError):
        JobCreateRequest(**_valid_payload(tone="x" * 201))
