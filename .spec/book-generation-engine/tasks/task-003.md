---
task: 003
feature: book-generation-engine
status: pending
model: haiku
supervisor: software-cto
agent: ai-ml-expert
depends_on: [002]
---

# Task 003: ImageClient Abstraction (DALL-E 3 + Replicate Flux)

## Skills
- .kit/skills/data-science-ml/ai-engineer/SKILL.md
- .kit/skills/languages/python-patterns/SKILL.md
- .kit/rules/python/patterns.md

## Agents
- @ai-ml-expert

## Commands
- /task-handoff

> Load the skills, agents, and commands listed above before reading anything else. Do not load context not listed here.

---

## Objective

Implement the `ImageClient` abstraction in `worker/clients/image_client.py` that routes cover image generation to DALL-E 3 (via OpenAI SDK) or Flux (via Replicate HTTP API), returning raw `bytes`.

---

## Files

### Create
| File | Purpose |
|------|---------|
| `worker/clients/image_client.py` | ImageClient routing to DALL-E 3 or Replicate Flux |
| `tests/unit/test_image_client.py` | Unit tests for both providers + unsupported provider |

---

## Dependencies

```bash
# No new packages — openai and httpx already in pyproject.toml.
# Env vars already in .env.example:
# OPENAI_IMAGE_API_KEY, REPLICATE_API_TOKEN
```

---

## API Contracts

_(none — internal class)_

---

## Code Templates

### `worker/clients/image_client.py` (create this file exactly)
```python
"""Provider-agnostic image generation client."""
from __future__ import annotations

import httpx
import openai

from worker.clients.exceptions import UnsupportedProviderError

SUPPORTED_IMAGE_PROVIDERS = frozenset({"dall-e-3", "replicate-flux"})
REPLICATE_FLUX_MODEL = "black-forest-labs/flux-schnell"
REPLICATE_API_BASE = "https://api.replicate.com/v1"


class ImageClient:
    """Generates images via DALL-E 3 or Replicate Flux. Returns raw bytes."""

    def __init__(self, provider: str, api_key: str) -> None:
        if provider not in SUPPORTED_IMAGE_PROVIDERS:
            raise UnsupportedProviderError(
                f"Image provider '{provider}' not supported. Choose from: "
                f"{sorted(SUPPORTED_IMAGE_PROVIDERS)}"
            )
        self.provider = provider
        self.api_key = api_key

    def generate(self, prompt: str, width: int = 1024, height: int = 1536) -> bytes:
        """Generate image. Returns raw JPEG/PNG bytes."""
        if self.provider == "dall-e-3":
            return self._dalle3(prompt, width, height)
        if self.provider == "replicate-flux":
            return self._replicate_flux(prompt, width, height)
        raise UnsupportedProviderError(self.provider)

    def _dalle3(self, prompt: str, width: int, height: int) -> bytes:
        client = openai.OpenAI(api_key=self.api_key)
        # DALL-E 3 supports fixed sizes; map to nearest supported
        size = self._nearest_dalle_size(width, height)
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            n=1,
            size=size,
            response_format="b64_json",
        )
        import base64
        b64 = response.data[0].b64_json
        assert b64 is not None
        return base64.b64decode(b64)

    def _replicate_flux(self, prompt: str, width: int, height: int) -> bytes:
        headers = {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "version": REPLICATE_FLUX_MODEL,
            "input": {"prompt": prompt, "width": width, "height": height},
        }
        with httpx.Client(timeout=120.0) as client:
            response = client.post(
                f"{REPLICATE_API_BASE}/predictions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            prediction = response.json()
            prediction_id = prediction["id"]

            # Poll until complete
            for _ in range(60):
                import time
                time.sleep(2)
                poll = client.get(
                    f"{REPLICATE_API_BASE}/predictions/{prediction_id}",
                    headers=headers,
                )
                poll.raise_for_status()
                data = poll.json()
                if data["status"] == "succeeded":
                    image_url = data["output"][0]
                    img_response = client.get(image_url)
                    img_response.raise_for_status()
                    return img_response.content
                if data["status"] in ("failed", "canceled"):
                    raise RuntimeError(f"Replicate prediction {prediction_id} failed: {data.get('error')}")
        raise RuntimeError(f"Replicate prediction {prediction_id} timed out after 120s")

    @staticmethod
    def _nearest_dalle_size(width: int, height: int) -> str:
        """Map arbitrary dimensions to the nearest DALL-E 3 supported size."""
        if height > width:
            return "1024x1792"
        if width > height:
            return "1792x1024"
        return "1024x1024"
```

### `tests/unit/test_image_client.py` (create this file exactly)
```python
"""Unit tests for ImageClient."""
import base64
from unittest.mock import MagicMock, patch

import pytest

from worker.clients.exceptions import UnsupportedProviderError
from worker.clients.image_client import ImageClient


def test_unsupported_provider_raises_at_construction():
    with pytest.raises(UnsupportedProviderError, match="badprovider"):
        ImageClient(provider="badprovider", api_key="k")


def test_dalle3_returns_bytes():
    fake_bytes = b"\x89PNG fake image data"
    b64_data = base64.b64encode(fake_bytes).decode()
    mock_openai = MagicMock()
    mock_openai.images.generate.return_value = MagicMock(
        data=[MagicMock(b64_json=b64_data)]
    )
    with patch("worker.clients.image_client.openai.OpenAI", return_value=mock_openai):
        client = ImageClient(provider="dall-e-3", api_key="k")
        result = client.generate("A book cover", 1024, 1536)
    assert result == fake_bytes
    mock_openai.images.generate.assert_called_once()


def test_dalle3_portrait_maps_to_1024x1792():
    b64_data = base64.b64encode(b"img").decode()
    mock_openai = MagicMock()
    mock_openai.images.generate.return_value = MagicMock(
        data=[MagicMock(b64_json=b64_data)]
    )
    with patch("worker.clients.image_client.openai.OpenAI", return_value=mock_openai):
        client = ImageClient(provider="dall-e-3", api_key="k")
        client.generate("cover", 1024, 1536)
    call_kwargs = mock_openai.images.generate.call_args[1]
    assert call_kwargs["size"] == "1024x1792"


def test_replicate_flux_returns_bytes():
    fake_image_bytes = b"flux image bytes"

    def mock_post(*args, **kwargs):
        m = MagicMock()
        m.json.return_value = {"id": "pred-123"}
        m.raise_for_status.return_value = None
        return m

    def mock_get(url, **kwargs):
        m = MagicMock()
        if "predictions/pred-123" in url:
            m.json.return_value = {
                "status": "succeeded",
                "output": ["https://example.com/image.jpg"],
            }
        else:
            m.content = fake_image_bytes
        m.raise_for_status.return_value = None
        return m

    mock_http_client = MagicMock()
    mock_http_client.__enter__ = lambda s: mock_http_client
    mock_http_client.__exit__ = MagicMock(return_value=False)
    mock_http_client.post = mock_post
    mock_http_client.get = mock_get

    with patch("worker.clients.image_client.httpx.Client", return_value=mock_http_client), \
         patch("worker.clients.image_client.time.sleep"):
        client = ImageClient(provider="replicate-flux", api_key="k")
        result = client.generate("cover prompt", 1024, 1536)
    assert result == fake_image_bytes
```

---

## Codebase Context

### Key Code Snippets
```python
# worker/clients/exceptions.py:1-8
class UnsupportedProviderError(ValueError):
    """Raised at LLMClient construction when provider name is not recognised."""
    pass

class ProviderRateLimitError(RuntimeError):
    """Raised after max retries are exhausted on a provider rate-limit response."""
    pass
```

### Key Patterns in Use
- **Provider SDK isolation:** Only `image_client.py` imports `openai` for image generation. No other file does.
- **Return `bytes`:** The caller (Cover Engine) receives raw bytes and uploads to Supabase Storage. Never return URLs.
- **`UnsupportedProviderError` at construction:** Same pattern as `LLMClient`.
- **Replicate polling:** Max 60 iterations × 2s sleep = 120s timeout. Raise `RuntimeError` on timeout.

### Architecture Decisions Affecting This Task
- Cover Engine calls `image_client.generate(prompt, width=1024, height=1536)` — portrait orientation for KDP cover.
- DALL-E 3 `response_format="b64_json"` avoids downloading from a temporary URL.

---

## Handoff from Previous Task

**Files changed by previous task:** `worker/clients/llm_client.py`, `worker/clients/exceptions.py`, `tests/unit/test_llm_client.py`.
**Decisions made:** UnsupportedProviderError at construction pattern established. MAX_RETRIES=3 with exponential backoff.
**Context for this task:** LLMClient is complete and tested. Now build ImageClient with the same patterns.
**Open questions left:** _(none)_

---

## Implementation Steps

1. Create `worker/clients/image_client.py` — paste template exactly.
2. Create `tests/unit/test_image_client.py` — paste template exactly.
3. Run: `pytest tests/unit/test_image_client.py -v` — verify all 4 tests pass.
4. Run: `ruff check worker/clients/image_client.py` — verify zero lint errors.
5. Run: `mypy worker/clients/image_client.py` — verify zero type errors.

---

## Decision Rules

| Scenario | Action |
|----------|--------|
| Provider not in `SUPPORTED_IMAGE_PROVIDERS` | Raise `UnsupportedProviderError(f"Image provider '{provider}' not supported. Choose from: {sorted(SUPPORTED_IMAGE_PROVIDERS)}")` |
| DALL-E 3: height > width | Use `size="1024x1792"` |
| DALL-E 3: width > height | Use `size="1792x1024"` |
| DALL-E 3: width == height | Use `size="1024x1024"` |
| Replicate: status == "failed" or "canceled" | Raise `RuntimeError(f"Replicate prediction {prediction_id} failed: {data.get('error')}")` |
| Replicate: 60 poll iterations exhausted | Raise `RuntimeError(f"Replicate prediction {prediction_id} timed out after 120s")` |

---

## Acceptance Criteria

- [ ] WHEN `ImageClient(provider="badprovider", ...)` is called THEN `UnsupportedProviderError` is raised
- [ ] WHEN DALL-E 3 provider is used THEN raw bytes are returned and `openai.images.generate` is called
- [ ] WHEN Replicate Flux provider is used THEN HTTP POST to Replicate API is made and image bytes returned
- [ ] WHEN `pytest tests/unit/test_image_client.py` runs THEN all 4 tests pass
- [ ] WHEN `ruff check` runs THEN zero errors

---

## Handoff to Next Task

**Files changed:** _(fill via /task-handoff)_
**Decisions made:** _(fill via /task-handoff)_
**Context for next task:** _(fill via /task-handoff)_
**Open questions:** _(fill via /task-handoff)_
