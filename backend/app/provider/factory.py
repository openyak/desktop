"""Provider factory — creates the right provider instance by ID.

Lazy imports ensure that native SDK dependencies (anthropic, google-genai)
are only loaded when the provider is actually used.
"""

from __future__ import annotations

import logging

from app.provider.base import BaseProvider
from app.provider.catalog import PROVIDER_CATALOG

logger = logging.getLogger(__name__)


def create_provider(
    provider_id: str,
    api_key: str,
    *,
    base_url: str | None = None,
) -> BaseProvider:
    """Create a desktop provider by ID.

    Routes to the correct implementation:
    - "anthropic" → AnthropicDesktopProvider (native SDK via yakAgent)
    - "google"    → GeminiDesktopProvider (native SDK via yakAgent)
    - Others      → GenericOpenAIProvider (OpenAI-compatible)

    Args:
        provider_id: Provider ID from the catalog.
        api_key: API key for the provider.
        base_url: Override base URL (required for Azure).

    Raises:
        ValueError: If provider_id is not in the catalog.
        ImportError: If a native SDK is required but not installed.
    """
    pdef = PROVIDER_CATALOG.get(provider_id)
    if pdef is None:
        raise ValueError(
            f"Unknown provider: '{provider_id}'. "
            f"Available: {', '.join(sorted(PROVIDER_CATALOG.keys()))}"
        )

    if pdef.kind == "openrouter":
        from app.provider.openrouter import OpenRouterProvider
        return OpenRouterProvider(api_key)

    if pdef.kind == "native_anthropic":
        from app.provider.anthropic_provider import AnthropicDesktopProvider
        return AnthropicDesktopProvider(api_key=api_key)

    if pdef.kind == "native_gemini":
        from app.provider.gemini_provider import GeminiDesktopProvider
        return GeminiDesktopProvider(api_key=api_key)

    if pdef.kind in ("openai_compat", "openai_compat_azure"):
        from app.provider.generic_openai import GenericOpenAIProvider

        effective_url = base_url or pdef.base_url
        if not effective_url:
            raise ValueError(
                f"Provider '{provider_id}' requires a base_url. "
                f"Set OPENYAK_AZURE_OPENAI_BASE_URL for Azure."
            )
        return GenericOpenAIProvider(
            api_key=api_key,
            provider_id=provider_id,
            base_url=effective_url,
            default_headers=pdef.default_headers or None,
        )

    raise ValueError(f"Unknown provider kind: '{pdef.kind}' for provider '{provider_id}'")
