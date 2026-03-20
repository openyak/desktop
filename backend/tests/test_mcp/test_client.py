"""Tests for MCP client wrapper."""

from __future__ import annotations

import pytest

pytest.importorskip("mcp")

from unittest.mock import AsyncMock, MagicMock, patch

from app.mcp.client import McpClient, sanitise_name


class TestSanitiseName:
    def test_clean(self):
        assert sanitise_name("my_tool") == "my_tool"

    def test_special_chars(self):
        assert sanitise_name("my tool@v2!") == "my_tool_v2_"

    def test_hyphens(self):
        assert sanitise_name("my-tool") == "my-tool"


class TestToolId:
    def test_format(self):
        client = McpClient("server-1", {"type": "local"})
        assert client.tool_id("read_file") == "server-1_read_file"

    def test_sanitised(self):
        client = McpClient("my server", {"type": "local"})
        assert client.tool_id("my tool") == "my_server_my_tool"


class TestClientProperties:
    def test_server_type_local(self):
        c = McpClient("test", {"type": "local"})
        assert c.server_type == "local"

    def test_server_type_remote(self):
        c = McpClient("test", {"type": "remote", "url": "http://x"})
        assert c.server_type == "remote"

    def test_default_type(self):
        c = McpClient("test", {})
        assert c.server_type == "local"

    def test_default_timeout(self):
        c = McpClient("test", {})
        assert c.timeout == 30

    def test_custom_timeout(self):
        c = McpClient("test", {"timeout": 60})
        assert c.timeout == 60


class TestOAuthToken:
    def test_set_and_clear(self):
        c = McpClient("test", {})
        assert c._oauth_token is None
        c.set_oauth_token("tok123")
        assert c._oauth_token == "tok123"
        c.set_oauth_token(None)
        assert c._oauth_token is None


class TestListTools:
    def test_empty(self):
        c = McpClient("test", {})
        assert c.list_tools() == []

    def test_returns_copy(self):
        c = McpClient("test", {})
        c._tools = [MagicMock(), MagicMock()]
        tools = c.list_tools()
        assert len(tools) == 2
        assert tools is not c._tools


class TestCallTool:
    @pytest.mark.asyncio
    async def test_not_connected_raises(self):
        c = McpClient("test", {})
        with pytest.raises(RuntimeError, match="not connected"):
            await c.call_tool("read", {})

    @pytest.mark.asyncio
    async def test_delegates_to_session(self):
        c = McpClient("test", {})
        c._session = MagicMock()
        c._session.call_tool = AsyncMock(return_value="result")
        result = await c.call_tool("read", {"path": "/tmp"})
        c._session.call_tool.assert_awaited_once_with("read", {"path": "/tmp"})


class TestClose:
    @pytest.mark.asyncio
    async def test_resets_state(self):
        c = McpClient("test", {})
        c.status = "connected"
        c._tools = [MagicMock()]
        c._exit_stack = None
        await c.close()
        assert c.status == "disconnected"
        assert c._tools == []


class TestConnectStdio:
    @pytest.mark.asyncio
    async def test_missing_command_raises(self):
        c = McpClient("test", {"type": "local", "command": []})
        c._exit_stack = MagicMock()
        c._exit_stack.__aenter__ = AsyncMock()
        with pytest.raises(ValueError, match="command"):
            await c._connect_stdio()
