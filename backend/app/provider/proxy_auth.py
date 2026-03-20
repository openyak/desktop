"""Proxy token auto-refresh utility.

Refreshes expired JWT access tokens using the stored refresh token,
updating both the live provider and the persisted .env file.
"""

from __future__ import annotations

import asyncio
import logging

import httpx

logger = logging.getLogger(__name__)

_refresh_lock = asyncio.Lock()


async def refresh_proxy_token(
    settings: object,
    provider_registry: object,
) -> bool:
    """Refresh the proxy access token using the stored refresh token.

    Returns True if the token was successfully refreshed, False otherwise.
    Thread-safe: concurrent callers wait on a single refresh attempt.
    """
    from app.api.config import _update_env_file

    proxy_url = getattr(settings, "proxy_url", "")
    refresh_token = getattr(settings, "proxy_refresh_token", "")

    if not proxy_url or not refresh_token:
        logger.debug("Cannot refresh proxy token: missing proxy_url or refresh_token")
        return False

    async with _refresh_lock:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{proxy_url}/api/auth/refresh",
                    json={"refresh_token": refresh_token},
                    timeout=15.0,
                )

            if resp.status_code != 200:
                logger.warning(
                    "Proxy token refresh failed: HTTP %d — %s",
                    resp.status_code,
                    resp.text[:200],
                )
                return False

            data = resp.json()
            new_access = data.get("access_token", "")
            new_refresh = data.get("refresh_token", "")

            if not new_access:
                logger.warning("Proxy token refresh returned empty access_token")
                return False

            # Update runtime settings
            settings.proxy_token = new_access  # type: ignore[attr-defined]
            if new_refresh:
                settings.proxy_refresh_token = new_refresh  # type: ignore[attr-defined]

            # Persist to .env
            _update_env_file("OPENYAK_PROXY_TOKEN", new_access)
            if new_refresh:
                _update_env_file("OPENYAK_PROXY_REFRESH_TOKEN", new_refresh)

            # Update the live provider's API key
            provider = getattr(provider_registry, "get_provider", lambda _: None)("openrouter")
            if provider and hasattr(provider, "update_api_key"):
                provider.update_api_key(new_access)

            logger.info("Proxy token refreshed successfully")
            return True

        except Exception as e:
            logger.warning("Proxy token refresh error: %s", e)
            return False
