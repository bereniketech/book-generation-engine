class UnsupportedProviderError(ValueError):
    """Raised at LLMClient construction when provider name is not recognised."""
    pass


class ProviderRateLimitError(RuntimeError):
    """Raised after max retries are exhausted on a provider rate-limit response."""
    pass
