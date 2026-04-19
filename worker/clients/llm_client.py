"""Provider-agnostic LLM client. No engine imports a provider SDK directly."""
from __future__ import annotations

import asyncio
import os
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

# ---------------------------------------------------------------------------
# Fallback chain configuration (module-level, read once at import time)
# ---------------------------------------------------------------------------
LLM_FALLBACK_CHAIN: list[str] = [
    p.strip()
    for p in os.getenv("LLM_FALLBACK_CHAIN", "anthropic,openai,gemini").split(",")
    if p.strip()
]
MAX_LLM_RETRIES: int = int(os.getenv("MAX_LLM_RETRIES", "2"))


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


# ---------------------------------------------------------------------------
# Module-level fallback chain functions
# ---------------------------------------------------------------------------

async def call_llm_with_fallback(
    prompt: str,
    job_id: str,
    stage: str,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> str:
    """Call LLM providers in fallback chain order. Returns text response.

    Tries each provider in LLM_FALLBACK_CHAIN up to MAX_LLM_RETRIES times.
    Raises RuntimeError if all providers are exhausted.
    """
    last_error: Exception | None = None

    for provider_name in LLM_FALLBACK_CHAIN:
        for attempt in range(1, MAX_LLM_RETRIES + 1):
            try:
                response = await _call_provider(
                    provider=provider_name,
                    prompt=prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                if provider_name != LLM_FALLBACK_CHAIN[0] or attempt > 1:
                    log.info(
                        "worker.llm.fallback",
                        job_id=job_id,
                        stage=stage,
                        provider_used=provider_name,
                        attempt=attempt,
                    )
                return response
            except Exception as exc:
                last_error = exc
                log.warning(
                    "worker.llm.attempt_failed",
                    job_id=job_id,
                    stage=stage,
                    provider=provider_name,
                    attempt=attempt,
                    max_retries=MAX_LLM_RETRIES,
                    error=str(exc),
                )
                if attempt < MAX_LLM_RETRIES:
                    await asyncio.sleep(2 ** attempt)

        if provider_name != LLM_FALLBACK_CHAIN[-1]:
            next_provider = LLM_FALLBACK_CHAIN[LLM_FALLBACK_CHAIN.index(provider_name) + 1]
            log.warning(
                "worker.llm.provider_exhausted",
                job_id=job_id,
                stage=stage,
                from_provider=provider_name,
                to_provider=next_provider,
                reason=str(last_error),
            )

    log.error(
        "worker.llm.all_providers_failed",
        job_id=job_id,
        stage=stage,
        chain=LLM_FALLBACK_CHAIN,
        error=str(last_error),
    )
    raise RuntimeError(
        f"All LLM providers failed for job {job_id} stage {stage}: {last_error}"
    )


async def _call_provider(
    provider: str,
    prompt: str,
    temperature: float | None,
    max_tokens: int | None,
) -> str:
    """Dispatch to the correct provider client. Returns response text."""
    if provider == "anthropic":
        return await _call_anthropic(prompt, temperature, max_tokens)
    elif provider == "openai":
        return await _call_openai(prompt, temperature, max_tokens)
    elif provider == "gemini":
        return await _call_gemini(prompt, temperature, max_tokens)
    elif provider == "ollama":
        return await _call_ollama(prompt, temperature, max_tokens)
    else:
        raise ValueError(f"Unknown provider: {provider}")


async def _call_anthropic(
    prompt: str,
    temperature: float | None,
    max_tokens: int | None,
) -> str:
    """Call Anthropic Claude. Requires ANTHROPIC_API_KEY env var."""
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise NotImplementedError("ANTHROPIC_API_KEY is not set")
    client = anthropic.AsyncAnthropic(api_key=api_key)
    kwargs: dict = {
        "model": os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6"),
        "max_tokens": max_tokens or 8192,
        "messages": [{"role": "user", "content": prompt}],
    }
    if temperature is not None:
        kwargs["temperature"] = temperature
    message = await client.messages.create(**kwargs)
    return message.content[0].text  # type: ignore[union-attr]


async def _call_openai(
    prompt: str,
    temperature: float | None,
    max_tokens: int | None,
) -> str:
    """Call OpenAI. Requires OPENAI_API_KEY env var."""
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        raise NotImplementedError("OPENAI_API_KEY is not set")
    client = openai.AsyncOpenAI(api_key=api_key)
    kwargs: dict = {
        "model": os.getenv("OPENAI_MODEL", "gpt-4o"),
        "messages": [{"role": "user", "content": prompt}],
    }
    if temperature is not None:
        kwargs["temperature"] = temperature
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens
    response = await client.chat.completions.create(**kwargs)
    return response.choices[0].message.content or ""


async def _call_gemini(
    prompt: str,
    temperature: float | None,
    max_tokens: int | None,
) -> str:
    """Call Google Gemini via generativeai. Requires GOOGLE_API_KEY env var."""
    api_key = os.getenv("GOOGLE_API_KEY", "")
    if not api_key:
        raise NotImplementedError("GOOGLE_API_KEY is not set")
    genai.configure(api_key=api_key)
    model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-pro")
    generation_config: dict = {}
    if temperature is not None:
        generation_config["temperature"] = temperature
    if max_tokens is not None:
        generation_config["max_output_tokens"] = max_tokens
    gm = genai.GenerativeModel(model_name, generation_config=generation_config or None)
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(None, gm.generate_content, prompt)
    return response.text


async def _call_ollama(
    prompt: str,
    temperature: float | None,
    max_tokens: int | None,
) -> str:
    """Call Ollama via OpenAI-compatible API. Requires OLLAMA_BASE_URL env var."""
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
    client = openai.AsyncOpenAI(api_key="ollama", base_url=base_url)
    kwargs: dict = {
        "model": os.getenv("OLLAMA_MODEL", "llama3"),
        "messages": [{"role": "user", "content": prompt}],
    }
    if temperature is not None:
        kwargs["temperature"] = temperature
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens
    response = await client.chat.completions.create(**kwargs)
    return response.choices[0].message.content or ""
