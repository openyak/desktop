"""Bash tool tests."""

import platform

import pytest

from app.schemas.agent import AgentInfo
from app.tool.builtin.bash import BashTool
from app.tool.context import ToolContext


def _make_ctx() -> ToolContext:
    return ToolContext(
        session_id="test-session",
        message_id="test-msg",
        agent=AgentInfo(name="test", description="", mode="primary"),
        call_id="test-call",
    )


class TestBashTool:
    @pytest.fixture
    def tool(self):
        return BashTool()

    @pytest.mark.asyncio
    async def test_echo(self, tool: BashTool):
        if platform.system() == "Windows":
            result = await tool.execute({"command": "echo hello"}, _make_ctx())
        else:
            result = await tool.execute({"command": "echo hello"}, _make_ctx())
        assert "hello" in result.output

    @pytest.mark.asyncio
    async def test_exit_code_nonzero(self, tool: BashTool):
        if platform.system() == "Windows":
            result = await tool.execute({"command": "cmd /c exit 1"}, _make_ctx())
        else:
            result = await tool.execute({"command": "exit 1"}, _make_ctx())
        assert result.error is not None
        assert "exit code" in result.error.lower() or "1" in str(result.metadata.get("exit_code"))

    @pytest.mark.asyncio
    async def test_timeout(self, tool: BashTool):
        if platform.system() == "Windows":
            cmd = "ping -n 10 127.0.0.1"
        else:
            cmd = "sleep 10"
        result = await tool.execute({"command": cmd, "timeout": 1}, _make_ctx())
        assert "timed out" in (result.error or "").lower()

    @pytest.mark.asyncio
    async def test_captures_stderr(self, tool: BashTool):
        if platform.system() == "Windows":
            result = await tool.execute({"command": "echo err 1>&2"}, _make_ctx())
        else:
            result = await tool.execute({"command": "echo err >&2"}, _make_ctx())
        assert "err" in result.output
