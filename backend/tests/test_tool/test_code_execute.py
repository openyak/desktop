"""Tests for app.tool.builtin.code_execute execution behavior."""

from __future__ import annotations

import pytest

from app.schemas.agent import AgentInfo
from app.tool.builtin.code_execute import CodeExecuteTool
from app.tool.context import ToolContext


def _make_ctx() -> ToolContext:
    return ToolContext(
        session_id="test-session",
        message_id="test-msg",
        agent=AgentInfo(name="test", description="", mode="primary"),
        call_id="test-call",
    )


class TestCodeExecuteExecution:
    @pytest.fixture
    def tool(self):
        return CodeExecuteTool()

    @pytest.mark.asyncio
    async def test_simple_print(self, tool: CodeExecuteTool):
        result = await tool.execute({"code": "print('hello')"}, _make_ctx())
        assert "hello" in result.output

    @pytest.mark.asyncio
    async def test_unicode_print(self, tool: CodeExecuteTool):
        """Ensure Chinese/Unicode characters are not garbled."""
        result = await tool.execute(
            {"code": "print('你好世界')"}, _make_ctx()
        )
        assert "你好世界" in result.output
