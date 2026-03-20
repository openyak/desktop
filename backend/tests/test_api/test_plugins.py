"""Tests for plugin management API endpoints."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock

pytestmark = pytest.mark.asyncio


@pytest.fixture
def _mock_pm(app_client):
    """Inject a mock PluginManager."""
    pm = MagicMock()
    pm.status.return_value = {
        "office": {"enabled": True, "skills": ["pdf", "docx"]},
        "github": {"enabled": False, "skills": []},
    }
    pm.detail.return_value = {"name": "office", "description": "Office", "enabled": True}
    pm.enable.return_value = True
    pm.disable.return_value = True
    app_client.app.state.plugin_manager = pm
    return pm


class TestPluginStatus:
    async def test_returns_all(self, app_client, _mock_pm):
        resp = await app_client.get("/api/plugins/status")
        assert resp.status_code == 200
        assert "office" in resp.json()["plugins"]

    async def test_no_manager(self, app_client):
        app_client.app.state.plugin_manager = None
        resp = await app_client.get("/api/plugins/status")
        assert resp.status_code == 200
        assert resp.json() == {"plugins": {}}


class TestPluginDetail:
    async def test_existing(self, app_client, _mock_pm):
        resp = await app_client.get("/api/plugins/office")
        assert resp.status_code == 200
        assert resp.json()["name"] == "office"

    async def test_not_found(self, app_client, _mock_pm):
        _mock_pm.detail.return_value = None
        resp = await app_client.get("/api/plugins/nope")
        assert resp.status_code == 404

    async def test_no_manager(self, app_client):
        app_client.app.state.plugin_manager = None
        resp = await app_client.get("/api/plugins/anything")
        assert resp.status_code == 404


class TestEnablePlugin:
    async def test_success(self, app_client, _mock_pm):
        resp = await app_client.post("/api/plugins/github/enable")
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    async def test_no_manager(self, app_client):
        app_client.app.state.plugin_manager = None
        resp = await app_client.post("/api/plugins/x/enable")
        assert resp.status_code == 200
        assert resp.json()["success"] is False


class TestDisablePlugin:
    async def test_success(self, app_client, _mock_pm):
        resp = await app_client.post("/api/plugins/office/disable")
        assert resp.status_code == 200
        assert resp.json()["success"] is True
