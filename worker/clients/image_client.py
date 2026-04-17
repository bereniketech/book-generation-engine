"""Provider-agnostic image generation client."""
from __future__ import annotations

import base64
import time

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
                    raise RuntimeError(
                        f"Replicate prediction {prediction_id} failed: {data.get('error')}"
                    )
        raise RuntimeError(f"Replicate prediction {prediction_id} timed out after 120s")

    @staticmethod
    def _nearest_dalle_size(width: int, height: int) -> str:
        """Map arbitrary dimensions to the nearest DALL-E 3 supported size."""
        if height > width:
            return "1024x1792"
        if width > height:
            return "1792x1024"
        return "1024x1024"
