"""Tests for connector management API endpoints."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

pytestmark = pytest.mark.asyncio


@pytest.fixture
def _mock_cr(app_client):
    """Inject a richer mock ConnectorRegistry."""
    cr = MagicMock()
    cr.status.return_value = {
        "github": {"status": "connected", "error": None, "type": "remote", "tools": 3},
        "slack": {"status": "needs_auth", "error": None, "type": "remote", "tools": 0},
    }
    cr.enable = AsyncMock(return_value=True)
    cr.disable = AsyncMock(return_value=True)
    cr.reconnect = AsyncMock(return_value=True)
    cr.connect = AsyncMock(return_value={"auth_url": "https://ex.com/auth", "state": "abc"})
    cr.complete_auth = AsyncMock(return_value=True)
    cr.disconnect = AsyncMock(return_value=True)
    cr.get.return_value = MagicMock(enabled=True)
    cr.mcp_manager = MagicMock(_clients={}, _token_store=MagicMock())

    conn = MagicMock()
    conn.to_dict.return_value = {"id": "c1", "name": "Custom"}
    cr.register_custom.return_value = conn
    cr.remove_custom.return_value = True

    app_client.app.state.connector_registry = cr
    return cr


class TestListConnectors:
    async def test_with_registry(self, app_client, _mock_cr):
        resp = await app_client.get("/api/connectors")
        assert resp.status_code == 200
        assert "github" in resp.json()["connectors"]

    async def test_no_registry(self, app_client):
        app_client.app.state.connector_registry = None
        resp = await app_client.get("/api/connectors")
        assert resp.status_code == 200
        assert resp.json() == {"connectors": {}}


class TestConnectorDetail:
    async def test_existing(self, app_client, _mock_cr):
        resp = await app_client.get("/api/connectors/github")
        assert resp.status_code == 200
        assert resp.json()["status"] == "connected"

    async def test_not_found(self, app_client, _mock_cr):
        resp = await app_client.get("/api/connectors/nonexistent")
        assert resp.status_code == 404


class TestAddCustom:
    async def test_success(self, app_client, _mock_cr):
        resp = await app_client.post("/api/connectors", json={
            "id": "c1", "name": "Custom", "url": "https://ex.com",
        })
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    async def test_duplicate(self, app_client, _mock_cr):
        _mock_cr.register_custom.side_effect = ValueError("Dup")
        resp = await app_client.post("/api/connectors", json={
            "id": "dup", "name": "D", "url": "https://ex.com",
        })
        assert resp.status_code == 200
        assert resp.json()["success"] is False


class TestRemoveCustom:
    async def test_success(self, app_client, _mock_cr):
        resp = await app_client.delete("/api/connectors/c1")
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    async def test_not_custom(self, app_client, _mock_cr):
        _mock_cr.remove_custom.return_value = False
        resp = await app_client.delete("/api/connectors/builtin")
        assert resp.status_code == 200
        assert resp.json()["success"] is False


class TestEnableDisable:
    async def test_enable(self, app_client, _mock_cr):
        resp = await app_client.post("/api/connectors/github/enable")
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    async def test_disable(self, app_client, _mock_cr):
        resp = await app_client.post("/api/connectors/slack/disable")
        assert resp.status_code == 200
        assert resp.json()["success"] is True


class TestOAuthCallback:
    async def test_callback(self, app_client, _mock_cr):
        resp = await app_client.get("/api/connectors/oauth/callback", params={"code": "c", "state": "s"})
        assert resp.status_code == 200
        _mock_cr.complete_auth.assert_awaited_once_with("s", "c")
