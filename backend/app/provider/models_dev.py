"""models.dev integration — remote model metadata source.

Fetches model catalogs (pricing, capabilities, limits) from models.dev,
caches locally, and falls back to yakAgent's hardcoded catalog when offline.

Usage:
    from app.provider.models_dev import models_dev

    # Get all models for a provider
    provider_data = await models_dev.get_provider("anthropic")
    models = provider_data["models"]  # dict of model_id -> model metadata

    # Force refresh from remote
    await models_dev.refresh()
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)

MODELS_DEV_URL = "https://models.dev/api.json"
CACHE_TTL_SECONDS = 3600  # 1 hour
_FETCH_TIMEOUT = 15.0  # seconds


# Provider IDs in models.dev → our provider IDs
# Most are 1:1, but some differ
_PROVIDER_ID_MAP: dict[str, str] = {
    "anthropic": "anthropic",
    "openai": "openai",
    "google": "google",
    "mistral": "mistral",
    "xai": "xai",
    "groq": "groq",
    "cohere": "cohere",
    "deepinfra": "deepinfra",
    "perplexity": "perplexity",
    "fireworks": "fireworks",
    "cerebras": "cerebras",
    "togetherai": "together",
    "deepseek": "deepseek",
    "azure": "azure",
}


class ModelsDevService:
    """Fetches and caches model metadata from models.dev."""

    def __init__(self, cache_dir: Path | None = None):
        self._cache_dir = cache_dir or Path.cwd() / "data"
        self._cache_file = self._cache_dir / "models_dev_cache.json"
        self._data: dict[str, Any] | None = None
        self._last_fetch: float = 0

    async def get_provider(self, provider_id: str) -> dict[str, Any] | None:
        """Get models.dev data for a provider, fetching/caching as needed."""
        data = await self._ensure_loaded()
        # Try direct ID first, then reverse-map
        if provider_id in data:
            return data[provider_id]
        # Reverse lookup: our ID → models.dev ID
        for mdev_id, our_id in _PROVIDER_ID_MAP.items():
            if our_id == provider_id and mdev_id in data:
                return data[mdev_id]
        return None

    async def get_models(self, provider_id: str) -> list[dict[str, Any]]:
        """Get model list for a provider, converted to our ModelInfo-compatible format."""
        provider_data = await self.get_provider(provider_id)
        if not provider_data:
            return []

        our_pid = _PROVIDER_ID_MAP.get(provider_id, provider_id)
        models_raw = provider_data.get("models", {})
        result = []
        for model_id, m in models_raw.items():
            # Skip models without pricing — they'd show as $0 (misleading)
            cost = m.get("cost")
            if not cost or (cost.get("input", 0) == 0 and cost.get("output", 0) == 0):
                continue

            # Skip deprecated/alpha models
            status = m.get("status")
            if status in ("deprecated", "alpha"):
                continue

            limit = m.get("limit") or {}
            modalities = m.get("modalities") or {}

            result.append({
                "id": model_id,
                "name": m.get("name", model_id),
                "provider_id": our_pid,
                "capabilities": {
                    "function_calling": m.get("tool_call", False),
                    "vision": "image" in (modalities.get("input") or []),
                    "reasoning": m.get("reasoning", False),
                    "json_output": m.get("structured_output", False),
                    "max_context": limit.get("context", 4096),
                    "max_output": limit.get("output"),
                    "prompt_caching": "cache_read" in cost,
                },
                "pricing": {
                    "prompt": cost.get("input", 0),
                    "completion": cost.get("output", 0),
                },
                "metadata": {
                    "family": m.get("family"),
                    "release_date": m.get("release_date"),
                    "cache_read_price": cost.get("cache_read", 0),
                    "cache_write_price": cost.get("cache_write", 0),
                    "status": status,
                },
            })
        return result

    async def refresh(self) -> bool:
        """Force refresh from models.dev. Returns True on success."""
        try:
            async with httpx.AsyncClient(timeout=_FETCH_TIMEOUT) as client:
                resp = await client.get(MODELS_DEV_URL)
                resp.raise_for_status()
                data = resp.json()

            self._data = data
            self._last_fetch = time.time()

            # Persist to cache
            self._cache_dir.mkdir(parents=True, exist_ok=True)
            self._cache_file.write_text(
                json.dumps(data, separators=(",", ":")),
                encoding="utf-8",
            )
            logger.info(
                "models.dev: refreshed %d providers",
                len(data),
            )
            return True

        except Exception as e:
            logger.warning("models.dev: fetch failed: %s", e)
            return False

    async def _ensure_loaded(self) -> dict[str, Any]:
        """Load data from cache or remote, with fallback chain."""
        # Already in memory and fresh
        if self._data is not None and (time.time() - self._last_fetch) < CACHE_TTL_SECONDS:
            return self._data

        # Try disk cache
        if self._data is None and self._cache_file.exists():
            try:
                raw = self._cache_file.read_text(encoding="utf-8")
                self._data = json.loads(raw)
                self._last_fetch = self._cache_file.stat().st_mtime
                logger.debug("models.dev: loaded from cache (%d providers)", len(self._data))
            except Exception as e:
                logger.warning("models.dev: cache read failed: %s", e)

        # Cache is stale or missing — try remote
        if self._data is None or (time.time() - self._last_fetch) >= CACHE_TTL_SECONDS:
            await self.refresh()

        # Final fallback: empty dict (providers will use their own hardcoded models)
        if self._data is None:
            self._data = {}

        return self._data


# Singleton instance
models_dev = ModelsDevService()
