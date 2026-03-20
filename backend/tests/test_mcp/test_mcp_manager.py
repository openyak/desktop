"""Tests for MCP manager lifecycle."""

from __future__ import annotations

import pytest

pytest.importorskip("mcp")

from unittest.mock import AsyncMock, MagicMock, patch

from app.mcp.manager import McpManager


def _mock_client(name: str, status: str = "connected", tools: list | None = None):
    c = MagicMock()
    c.name = name
    c.status = status
    c.error = None
    c.server_type = "remote"
    c._oauth_token = None
    c.connect = AsyncMock()
    c.close = AsyncMock()
    c.set_oauth_token = MagicMock()
    c.list_tools = MagicMock(return_value=tools or [])
    return c


class TestStartup:
    @pytest.mark.asyncio
    async def test_connects_enabled(self):
        mgr = McpManager({"srv1": {"enabled": True, "url": "http://x"}})
        with patch("app.mcp.manager.McpClient") as MockClient:
            mc = _mock_client("srv1")
            MockClient.return_value = mc
            mgr._token_store = MagicMock(get=MagicMock(return_value=None))
            await mgr.startup()
        assert "srv1" in mgr._clients
        mc.connect.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_skips_disabled(self):
        mgr = McpManager({"srv1": {"enabled": False}})
        mgr._token_store = MagicMock()
        await mgr.startup()
        assert "srv1" not in mgr._clients


class TestShutdown:
    @pytest.mark.asyncio
    async def test_closes_all(self):
        mgr = McpManager({})
        c1 = _mock_client("a")
        c2 = _mock_client("b")
        mgr._clients = {"a": c1, "b": c2}
        await mgr.shutdown()
        c1.close.assert_awaited_once()
        c2.close.assert_awaited_once()
        assert mgr._clients == {}


class TestTools:
    def test_only_connected(self):
        mgr = McpManager({})
        c1 = _mock_client("a", "connected", [MagicMock()])
        c2 = _mock_client("b", "failed")
        mgr._clients = {"a": c1, "b": c2}
        with patch("app.mcp.manager.McpToolWrapper"):
            tools = mgr.tools()
        assert len(tools) == 1

    def test_empty(self):
        mgr = McpManager({})
        assert mgr.tools() == []


class TestStatus:
    def test_reports_all(self):
        mgr = McpManager({})
        mgr._clients = {
            "a": _mock_client("a", "connected"),
            "b": _mock_client("b", "needs_auth"),
        }
        status = mgr.status()
        assert status["a"]["status"] == "connected"
        assert status["b"]["status"] == "needs_auth"


class TestDisconnectAuth:
    @pytest.mark.asyncio
    async def test_clears_and_disconnects(self):
        mgr = McpManager({})
        mgr._token_store = MagicMock()
        c = _mock_client("srv1")
        mgr._clients = {"srv1": c}

        result = await mgr.disconnect_auth("srv1")
        assert result is True
        mgr._token_store.delete.assert_called_once_with("srv1")
        c.set_oauth_token.assert_called_once_with(None)
        c.close.assert_awaited_once()
        assert c.status == "needs_auth"


class TestCompleteAuth:
    @pytest.mark.asyncio
    async def test_unknown_state(self):
        mgr = McpManager({})
        result = await mgr.complete_auth("unknown_state", "code123")
        assert result is False
