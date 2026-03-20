"""Configuration management endpoints."""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.provider.openrouter import OpenRouterProvider
from app.schemas.provider import ApiKeyStatus, ApiKeyUpdate

logger = logging.getLogger(__name__)

router = APIRouter()

# Persist runtime config in current working directory.
#
# Desktop mode (`run.py`) changes cwd to the app data directory, so this
# becomes a writable per-user `.env` (instead of the read-only app bundle path
# when running from a mounted DMG volume).
# Server mode runs with `/opt/openyak-proxy` as working directory, so behavior
# remains compatible there as well.
_ENV_PATH = Path(".env")


def _mask_key(key: str) -> str:
    """Mask API key for display: show first 7 and last 4 chars."""
    if len(key) <= 11:
        return "****"
    return f"{key[:7]}...{key[-4:]}"


def _update_env_file(key: str, value: str) -> None:
    """Update or add a key=value pair in the backend .env file."""
    lines: list[str] = []
    found = False

    if _ENV_PATH.exists():
        lines = _ENV_PATH.read_text(encoding="utf-8").splitlines()
        for i, line in enumerate(lines):
            if line.startswith(f"{key}=") or line.startswith(f"{key} ="):
                lines[i] = f"{key}={value}"
                found = True
                break

    if not found:
        lines.append(f"{key}={value}")

    _ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _remove_env_key(key: str) -> None:
    """Remove a key from the backend .env file entirely."""
    if not _ENV_PATH.exists():
        return
    lines = _ENV_PATH.read_text(encoding="utf-8").splitlines()
    lines = [l for l in lines if not l.startswith(f"{key}=") and not l.startswith(f"{key} =")]
    _ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


@router.get("/config/api-key", response_model=ApiKeyStatus)
async def get_api_key_status(request: Request) -> ApiKeyStatus:
    """Get the current API key configuration status."""
    registry = request.app.state.provider_registry
    provider = registry.get_provider("openrouter")

    if provider is None or not getattr(provider, "_api_key", ""):
        return ApiKeyStatus(is_configured=False)

    return ApiKeyStatus(
        is_configured=True,
        masked_key=_mask_key(provider._api_key),
    )


@router.post("/config/api-key", response_model=ApiKeyStatus)
async def update_api_key(request: Request, body: ApiKeyUpdate) -> ApiKeyStatus:
    """Update the OpenRouter API key, validate it, and re-initialize the provider."""
    api_key = body.api_key.strip()
    if not api_key:
        raise HTTPException(status_code=400, detail="API key cannot be empty")

    # Validate by attempting to fetch models with the new key
    test_provider = OpenRouterProvider(api_key)
    try:
        models = await test_provider.list_models()
        if not models:
            raise HTTPException(
                status_code=400,
                detail="API key is valid but returned no models",
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.warning("API key validation failed: %s", e)
        raise HTTPException(
            status_code=400,
            detail=f"API key validation failed: {e}",
        )

    # Key is valid — replace the provider in the registry
    registry = request.app.state.provider_registry
    new_provider = OpenRouterProvider(api_key)
    registry.register(new_provider)

    # Refresh the model index so the frontend picks up the new models
    try:
        await registry.refresh_models()
    except Exception as e:
        logger.warning("Model refresh failed after API key update: %s — will retry on next request", e)

    # Persist to .env so it survives restarts
    _update_env_file("OPENYAK_OPENROUTER_API_KEY", api_key)

    return ApiKeyStatus(
        is_configured=True,
        masked_key=_mask_key(api_key),
        is_valid=True,
    )


@router.delete("/config/api-key", response_model=ApiKeyStatus)
async def delete_api_key(request: Request) -> ApiKeyStatus:
    """Delete the stored OpenRouter API key."""
    settings = request.app.state.settings
    settings.openrouter_api_key = ""
    _remove_env_key("OPENYAK_OPENROUTER_API_KEY")

    # Only unregister the provider if not in proxy mode.
    # In proxy mode the active "openrouter" provider belongs to the proxy,
    # not the direct API key — don't remove it.
    if not (settings.proxy_url and settings.proxy_token):
        registry = request.app.state.provider_registry
        registry.unregister("openrouter")

    return ApiKeyStatus(is_configured=False)


# ── OpenYak Account (proxy mode) ───────────────────────────────────────────

class OpenYakAccountStatus(BaseModel):
    is_connected: bool = False
    proxy_url: str = ""
    email: str = ""


class OpenYakAccountConnect(BaseModel):
    proxy_url: str  # e.g. "https://api.openyak.app"
    token: str  # JWT from proxy auth
    refresh_token: str = ""  # Refresh token for auto-renewal


class OpenYakAccountDisconnect(BaseModel):
    pass


@router.get("/config/openyak-account", response_model=OpenYakAccountStatus)
async def get_openyak_account_status(request: Request) -> OpenYakAccountStatus:
    """Check if an OpenYak account is connected (proxy mode active)."""
    settings = request.app.state.settings
    if settings.proxy_url and settings.proxy_token:
        return OpenYakAccountStatus(
            is_connected=True,
            proxy_url=settings.proxy_url,
        )
    return OpenYakAccountStatus(is_connected=False)


@router.post("/config/openyak-account", response_model=OpenYakAccountStatus)
async def connect_openyak_account(request: Request, body: OpenYakAccountConnect) -> OpenYakAccountStatus:
    """Connect an OpenYak account: switch provider to proxy mode.

    The local app will now route all LLM requests through the OpenYak
    cloud proxy, which handles billing transparently.
    """
    proxy_url = body.proxy_url.rstrip("/")
    token = body.token.strip()

    if not proxy_url or not token:
        raise HTTPException(400, "proxy_url and token are required")

    # Validate by trying to list models through the proxy
    test_provider = OpenRouterProvider(token, base_url=proxy_url + "/v1")
    try:
        models = await test_provider.list_models()
        if not models:
            raise HTTPException(400, "Proxy returned no models")
    except HTTPException:
        raise
    except Exception as e:
        logger.warning("OpenYak account connection failed: %s", e)
        raise HTTPException(400, f"Failed to connect to proxy: {e}")

    # Switch the provider registry to use the proxy
    registry = request.app.state.provider_registry
    new_provider = OpenRouterProvider(token, base_url=proxy_url + "/v1")
    registry.register(new_provider)
    try:
        await registry.refresh_models()
    except Exception as e:
        logger.warning("Model refresh failed after proxy connect: %s — will retry on next request", e)

    # Persist to .env and update runtime settings
    _update_env_file("OPENYAK_PROXY_URL", proxy_url)
    _update_env_file("OPENYAK_PROXY_TOKEN", token)
    settings = request.app.state.settings
    settings.proxy_url = proxy_url
    settings.proxy_token = token

    if body.refresh_token:
        _update_env_file("OPENYAK_PROXY_REFRESH_TOKEN", body.refresh_token)
        settings.proxy_refresh_token = body.refresh_token

    return OpenYakAccountStatus(is_connected=True, proxy_url=proxy_url)


@router.delete("/config/openyak-account", response_model=OpenYakAccountStatus)
async def disconnect_openyak_account(request: Request) -> OpenYakAccountStatus:
    """Disconnect OpenYak account: revert to local API key mode."""
    settings = request.app.state.settings

    # Clear proxy settings
    settings.proxy_url = ""
    settings.proxy_token = ""
    settings.proxy_refresh_token = ""
    _update_env_file("OPENYAK_PROXY_URL", "")
    _update_env_file("OPENYAK_PROXY_TOKEN", "")
    _remove_env_key("OPENYAK_PROXY_REFRESH_TOKEN")

    # Re-init provider with local key if available
    registry = request.app.state.provider_registry
    if settings.openrouter_api_key:
        provider = OpenRouterProvider(settings.openrouter_api_key)
        registry.register(provider)
        try:
            await registry.refresh_models()
        except Exception as e:
            logger.warning("Model refresh failed after disconnect: %s — will retry on next request", e)

    return OpenYakAccountStatus(is_connected=False)
