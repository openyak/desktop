"""Helper for registering a local OpenAI-compatible provider."""

from __future__ import annotations

from app.provider.generic_openai import GenericOpenAIProvider

LOCAL_PROVIDER_ID = "local"
LOCAL_BASE_URL_ENV = "OPENYAK_LOCAL_BASE_URL"


def create_local_provider(base_url: str) -> GenericOpenAIProvider:
    """Return a GenericOpenAIProvider for the provided local base URL."""
    return GenericOpenAIProvider(
        api_key="",
        provider_id=LOCAL_PROVIDER_ID,
        base_url=base_url,
    )
