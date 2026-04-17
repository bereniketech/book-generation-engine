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
