"""Tests for proxy token auto-refresh utility."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.provider.proxy_auth import refresh_proxy_token

pytestmark = pytest.mark.asyncio


def _settings(**kw):
    s = MagicMock()
    s.proxy_url = kw.get("proxy_url", "http://proxy")
    s.proxy_refresh_token = kw.get("proxy_refresh_token", "rt")
    s.proxy_token = "old"
    return s


def _registry(provider=None):
    reg = MagicMock()
    reg.get_provider.return_value = provider
    return reg


class TestRefreshProxyToken:
    async def test_success(self):
        settings = _settings()
        prov = MagicMock()
        reg = _registry(prov)

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"access_token": "new_at", "refresh_token": "new_rt"}

        with patch("app.provider.proxy_auth.httpx.AsyncClient") as MockClient:
            MockClient.return_value.__aenter__ = AsyncMock(return_value=MagicMock(
                post=AsyncMock(return_value=mock_resp),
            ))
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
            with patch("app.api.config._update_env_file"):
                result = await refresh_proxy_token(settings, reg)

        assert result is True
        assert settings.proxy_token == "new_at"
        assert settings.proxy_refresh_token == "new_rt"

    async def test_missing_url(self):
        settings = _settings(proxy_url="")
        result = await refresh_proxy_token(settings, _registry())
        assert result is False

    async def test_missing_refresh_token(self):
        settings = _settings(proxy_refresh_token="")
        result = await refresh_proxy_token(settings, _registry())
        assert result is False

    async def test_http_error(self):
        settings = _settings()
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "Internal Server Error"

        with patch("app.provider.proxy_auth.httpx.AsyncClient") as MockClient:
            MockClient.return_value.__aenter__ = AsyncMock(return_value=MagicMock(
                post=AsyncMock(return_value=mock_resp),
            ))
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await refresh_proxy_token(settings, _registry())

        assert result is False

    async def test_empty_access_token(self):
        settings = _settings()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"access_token": "", "refresh_token": ""}

        with patch("app.provider.proxy_auth.httpx.AsyncClient") as MockClient:
            MockClient.return_value.__aenter__ = AsyncMock(return_value=MagicMock(
                post=AsyncMock(return_value=mock_resp),
            ))
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await refresh_proxy_token(settings, _registry())

        assert result is False

    async def test_network_error(self):
        settings = _settings()
        with patch("app.provider.proxy_auth.httpx.AsyncClient") as MockClient:
            MockClient.return_value.__aenter__ = AsyncMock(return_value=MagicMock(
                post=AsyncMock(side_effect=Exception("timeout")),
            ))
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await refresh_proxy_token(settings, _registry())

        assert result is False
