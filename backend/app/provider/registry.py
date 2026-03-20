"""Provider registry — manages provider instances and model lookup."""

from __future__ import annotations

import logging

from app.provider.base import BaseProvider
from app.schemas.provider import ModelInfo, ProviderStatus

logger = logging.getLogger(__name__)


class ProviderRegistry:
    """Registry of LLM providers."""

    def __init__(self) -> None:
        self._providers: dict[str, BaseProvider] = {}
        self._model_index: dict[str, tuple[BaseProvider, ModelInfo]] = {}

    def register(self, provider: BaseProvider) -> None:
        """Register a provider."""
        self._providers[provider.id] = provider
        logger.info("Registered provider: %s", provider.id)

    def unregister(self, provider_id: str) -> None:
        """Remove a provider and its models from the index."""
        self._providers.pop(provider_id, None)
        self._model_index = {
            mid: (p, m)
            for mid, (p, m) in self._model_index.items()
            if p.id != provider_id
        }
        logger.info("Unregistered provider: %s", provider_id)

    def get_provider(self, provider_id: str) -> BaseProvider | None:
        """Get provider by ID."""
        return self._providers.get(provider_id)

    async def refresh_models(self) -> dict[str, list[ModelInfo]]:
        """Refresh model lists from all providers."""
        result: dict[str, list[ModelInfo]] = {}
        new_index: dict[str, tuple[BaseProvider, ModelInfo]] = {}

        failed: list[tuple[str, Exception]] = []
        for pid, provider in self._providers.items():
            try:
                # Clear provider cache to force fresh fetch from API
                provider.clear_cache()
                models = await provider.list_models()
                result[pid] = models
                for m in models:
                    new_index[m.id] = (provider, m)
            except Exception as e:
                logger.error("Failed to refresh models for %s: %s", pid, e)
                result[pid] = []
                failed.append((pid, e))

        # Update index with whatever succeeded — one provider's failure
        # shouldn't take down the others.
        if new_index or not failed:
            self._model_index = new_index

        # If ALL providers failed, raise the first error so callers
        # (e.g. startup token refresh) can still react.
        if failed and not new_index:
            raise failed[0][1]

        logger.info(
            "Model index: %d models across %d providers",
            len(self._model_index),
            len(self._providers),
        )
        return result

    def resolve_model(self, model_id: str) -> tuple[BaseProvider, ModelInfo] | None:
        """Resolve a model ID to its provider and info."""
        return self._model_index.get(model_id)

    def all_models(self) -> list[ModelInfo]:
        """All indexed models."""
        return [info for _, info in self._model_index.values()]

    async def health(self) -> dict[str, ProviderStatus]:
        """Health check all providers."""
        result = {}
        for pid, provider in self._providers.items():
            result[pid] = await provider.health_check()
        return result
