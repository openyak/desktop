"""Generic OpenAI-compatible provider.

Works with any provider that implements the /v1/chat/completions API:
OpenAI, Groq, DeepSeek, Mistral, xAI, Together AI, etc.

Model metadata is sourced from models.dev (remote, cached hourly),
with fallback to yakAgent's hardcoded catalog, then to the provider's
own /v1/models API endpoint.
"""

from __future__ import annotations

import logging
from typing import Any

from app.provider.openai_compat import OpenAICompatProvider
from app.schemas.provider import (
    ModelCapabilities,
    ModelInfo,
    ModelPricing,
    ProviderStatus,
)

logger = logging.getLogger(__name__)


class GenericOpenAIProvider(OpenAICompatProvider):
    """OpenAI-compatible provider with configurable provider ID and known models."""

    def __init__(
        self,
        api_key: str,
        *,
        provider_id: str,
        base_url: str,
        default_headers: dict[str, str] | None = None,
    ):
        super().__init__(
            api_key=api_key,
            base_url=base_url,
            default_headers=default_headers,
        )
        self._api_key = api_key
        self._provider_id = provider_id
        self._models_cache: list[ModelInfo] | None = None

    @property
    def id(self) -> str:
        return self._provider_id

    async def list_models(self) -> list[ModelInfo]:
        """Return models with metadata. Merges models.dev + yakAgent catalog + API."""
        if self._models_cache is not None:
            return self._models_cache

        # 1. Start with models.dev (remote, cached, best pricing)
        models = await self._load_models_dev()

        # 2. Merge yakAgent catalog (fills gaps for models.dev doesn't cover)
        seen_ids = {m.id for m in models}
        for m in self._load_catalog_models():
            if m.id not in seen_ids:
                models.append(m)
                seen_ids.add(m.id)

        # 3. Last resort: provider's own /v1/models API (no pricing)
        if not models:
            models = await self._fetch_api_models()

        self._models_cache = models
        return models

    def clear_cache(self) -> None:
        self._models_cache = None

    async def _load_models_dev(self) -> list[ModelInfo]:
        """Load models from models.dev (remote source of truth)."""
        try:
            from app.provider.models_dev import models_dev

            raw_models = await models_dev.get_models(self._provider_id)
            if not raw_models:
                return []

            models = []
            for m in raw_models:
                caps = m.get("capabilities", {})
                pricing = m.get("pricing", {})
                models.append(ModelInfo(
                    id=m["id"],
                    name=m.get("name", m["id"]),
                    provider_id=self._provider_id,
                    capabilities=ModelCapabilities(
                        function_calling=caps.get("function_calling", True),
                        vision=caps.get("vision", False),
                        reasoning=caps.get("reasoning", False),
                        json_output=caps.get("json_output", False),
                        max_context=caps.get("max_context", 4096),
                        max_output=caps.get("max_output"),
                        prompt_caching=caps.get("prompt_caching", False),
                    ),
                    pricing=ModelPricing(
                        prompt=pricing.get("prompt", 0),
                        completion=pricing.get("completion", 0),
                    ),
                    metadata=m.get("metadata", {}),
                ))
            logger.debug("models.dev: loaded %d models for %s", len(models), self._provider_id)
            return models
        except Exception as e:
            logger.debug("models.dev unavailable for %s: %s", self._provider_id, e)
            return []

    def _load_catalog_models(self) -> list[ModelInfo]:
        """Fallback: load from yakAgent hardcoded catalog."""
        try:
            from yakagent.provider.catalog import PROVIDERS

            pdef = PROVIDERS.get(self._provider_id)
            if pdef is None or not pdef.models:
                return []

            models = []
            for model_id, info in pdef.models.items():
                models.append(ModelInfo(
                    id=model_id,
                    name=info.get("name", model_id),
                    provider_id=self._provider_id,
                    capabilities=ModelCapabilities(
                        function_calling=True,
                        vision=info.get("vision", False),
                        reasoning=info.get("reasoning", False),
                        max_context=info.get("context", 4096),
                        max_output=info.get("output", 4096),
                    ),
                    pricing=ModelPricing(
                        prompt=info.get("prompt", 0),
                        completion=info.get("completion", 0),
                    ),
                ))
            return models
        except ImportError:
            return []

    async def _fetch_api_models(self) -> list[ModelInfo]:
        """Last resort: fetch models from the provider's /v1/models endpoint."""
        try:
            response = await self._client.models.list()
            models = []
            for m in response.data:
                models.append(ModelInfo(
                    id=m.id,
                    name=m.id,
                    provider_id=self._provider_id,
                ))
            return models
        except Exception as e:
            logger.warning("Failed to fetch models from %s API: %s", self._provider_id, e)
            return []
