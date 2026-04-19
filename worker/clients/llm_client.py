"""Provider-agnostic LLM client. No engine imports a provider SDK directly."""
from __future__ import annotations

import asyncio
import time
from typing import Literal

import anthropic
import google.generativeai as genai
import openai

from worker.clients.exceptions import ProviderRateLimitError, UnsupportedProviderError
from app.core.logging import get_logger

log = get_logger(__name__)

SUPPORTED_PROVIDERS = frozenset({"anthropic", "openai", "google", "ollama", "openai-compatible"})
MAX_RETRIES = 3
BACKOFF_BASE = 0.5  # seconds


class LLMClient:
    """Single interface for all LLM providers. Constructed once per job."""

    def __init__(
        self,
        provider: Literal["anthropic", "openai", "google", "ollama", "openai-compatible"],
        model: str,
        api_key: str,
        base_url: str | None = None,
    ) -> None:
        if provider not in SUPPORTED_PROVIDERS:
            raise UnsupportedProviderError(
                f"Provider '{provider}' is not supported. "
                f"Choose from: {sorted(SUPPORTED_PROVIDERS)}"
            )
        self.provider = provider
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self._client = self._build_client()

    def _build_client(self) -> object:
        if self.provider == "anthropic":
            return anthropic.Anthropic(api_key=self.api_key)
        if self.provider in ("openai", "openai-compatible"):
            kwargs: dict = {"api_key": self.api_key}
            if self.base_url:
                kwargs["base_url"] = self.base_url
            return openai.OpenAI(**kwargs)
        if self.provider == "ollama":
            return openai.OpenAI(
                api_key="ollama",
                base_url=self.base_url or "http://localhost:11434/v1",
            )
        if self.provider == "google":
            genai.configure(api_key=self.api_key)
            return genai.GenerativeModel(self.model)
        raise UnsupportedProviderError(self.provider)  # unreachable but satisfies mypy

    def complete(
        self,
        prompt: str,
        system_prompt: str = "",
        job_id: str = "",
        stage: str = "",
    ) -> str:
        """Synchronous completion. Retries on rate-limit up to MAX_RETRIES times."""
        for attempt in range(MAX_RETRIES):
            try:
                return self._dispatch_sync(prompt, system_prompt, job_id=job_id, stage=stage)
            except (openai.RateLimitError, anthropic.RateLimitError) as exc:
                if attempt == MAX_RETRIES - 1:
                    raise ProviderRateLimitError(
                        f"Provider '{self.provider}' rate-limited after {MAX_RETRIES} retries."
                    ) from exc
                time.sleep(BACKOFF_BASE * (2**attempt))
        raise ProviderRateLimitError("Unreachable — loop exhausted.")

    async def acomplete(
        self,
        prompt: str,
        system_prompt: str = "",
        job_id: str = "",
        stage: str = "",
    ) -> str:
        """Async completion. Retries on rate-limit up to MAX_RETRIES times."""
        for attempt in range(MAX_RETRIES):
            try:
                return await self._dispatch_async(
                    prompt, system_prompt, job_id=job_id, stage=stage
                )
            except (openai.RateLimitError, anthropic.RateLimitError) as exc:
                if attempt == MAX_RETRIES - 1:
                    raise ProviderRateLimitError(
                        f"Provider '{self.provider}' rate-limited after {MAX_RETRIES} retries."
                    ) from exc
                await asyncio.sleep(BACKOFF_BASE * (2**attempt))
        raise ProviderRateLimitError("Unreachable — loop exhausted.")

    def _record_usage_sync(
        self, job_id: str, stage: str, input_tokens: int, output_tokens: int
    ) -> None:
        """Fire-and-forget token usage recording (sync wrapper)."""
        if not job_id:
            return
        try:
            import asyncio as _asyncio
            from app.services.token_tracker import record_usage

            loop = _asyncio.new_event_loop()
            loop.run_until_complete(
                record_usage(
                    job_id=job_id,
                    stage=stage,
                    provider=self.provider,
                    model=self.model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                )
            )
            loop.close()
        except Exception as exc:
            log.error("token_usage.sync_record_failed", job_id=job_id, error=str(exc))

    def _dispatch_sync(
        self, prompt: str, system_prompt: str, job_id: str = "", stage: str = ""
    ) -> str:
        if self.provider == "anthropic":
            client: anthropic.Anthropic = self._client  # type: ignore[assignment]
            message = client.messages.create(
                model=self.model,
                max_tokens=8192,
                system=system_prompt,
                messages=[{"role": "user", "content": prompt}],
            )
            if job_id and hasattr(message, "usage"):
                self._record_usage_sync(
                    job_id=job_id,
                    stage=stage,
                    input_tokens=getattr(message.usage, "input_tokens", 0),
                    output_tokens=getattr(message.usage, "output_tokens", 0),
                )
            return message.content[0].text  # type: ignore[union-attr]
        if self.provider in ("openai", "openai-compatible", "ollama"):
            client_oa: openai.OpenAI = self._client  # type: ignore[assignment]
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            response = client_oa.chat.completions.create(
                model=self.model,
                messages=messages,  # type: ignore[arg-type]
            )
            if job_id and hasattr(response, "usage") and response.usage:
                self._record_usage_sync(
                    job_id=job_id,
                    stage=stage,
                    input_tokens=getattr(response.usage, "prompt_tokens", 0),
                    output_tokens=getattr(response.usage, "completion_tokens", 0),
                )
            return response.choices[0].message.content or ""
        if self.provider == "google":
            gm: genai.GenerativeModel = self._client  # type: ignore[assignment]
            response = gm.generate_content(
                f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
            )
            if job_id and hasattr(response, "usage_metadata"):
                self._record_usage_sync(
                    job_id=job_id,
                    stage=stage,
                    input_tokens=getattr(response.usage_metadata, "prompt_token_count", 0),
                    output_tokens=getattr(
                        response.usage_metadata, "candidates_token_count", 0
                    ),
                )
            return response.text
        raise UnsupportedProviderError(self.provider)

    async def _dispatch_async(
        self, prompt: str, system_prompt: str, job_id: str = "", stage: str = ""
    ) -> str:
        # Run sync dispatch in executor to avoid blocking the event loop.
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self._dispatch_sync, prompt, system_prompt, job_id, stage
        )
