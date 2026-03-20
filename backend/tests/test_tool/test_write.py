"""Tests for app.tool.builtin.write — file write tool."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.schemas.agent import AgentInfo
from app.tool.builtin.write import WriteTool
from app.tool.context import ToolContext


def _make_ctx(workspace: str | None = None) -> ToolContext:
    return ToolContext(
        session_id="test-session",
        message_id="test-msg",
        agent=AgentInfo(name="test", description="", mode="primary"),
        call_id="test-call",
        workspace=workspace,
    )


class TestWriteTool:
    @pytest.fixture
    def tool(self):
        return WriteTool()

    @pytest.mark.asyncio
    async def test_create_new_file(self, tool: WriteTool, tmp_path: Path):
        f = tmp_path / "new.txt"
        result = await tool.execute(
            {"file_path": str(f), "content": "hello\nworld\n"},
            _make_ctx(),
        )
        assert result.success
        assert f.read_text() == "hello\nworld\n"
        assert "Created" in result.output

    @pytest.mark.asyncio
    async def test_overwrite_existing(self, tool: WriteTool, tmp_path: Path):
        f = tmp_path / "existing.txt"
        f.write_text("old content")
        result = await tool.execute(
            {"file_path": str(f), "content": "new content"},
            _make_ctx(),
        )
        assert result.success
        assert f.read_text() == "new content"
        assert "Updated" in result.output

    @pytest.mark.asyncio
    async def test_creates_parent_dirs(self, tool: WriteTool, tmp_path: Path):
        f = tmp_path / "a" / "b" / "c" / "file.txt"
        result = await tool.execute(
            {"file_path": str(f), "content": "deep"},
            _make_ctx(),
        )
        assert result.success
        assert f.read_text() == "deep"

    @pytest.mark.asyncio
    async def test_line_count_in_output(self, tool: WriteTool, tmp_path: Path):
        f = tmp_path / "lines.txt"
        result = await tool.execute(
            {"file_path": str(f), "content": "a\nb\nc\n"},
            _make_ctx(),
        )
        assert result.success
        assert "3" in result.output  # 3 lines

    @pytest.mark.asyncio
    async def test_workspace_violation(self, tool: WriteTool, tmp_path: Path):
        result = await tool.execute(
            {"file_path": "/etc/should-not-write", "content": "bad"},
            _make_ctx(workspace=str(tmp_path)),
        )
        assert not result.success

    @pytest.mark.asyncio
    async def test_relative_path_openyak_written(self, tool: WriteTool, tmp_path: Path):
        result = await tool.execute(
            {"file_path": "output.txt", "content": "relative"},
            _make_ctx(workspace=str(tmp_path)),
        )
        assert result.success
        expected = tmp_path / "openyak_written" / "output.txt"
        assert expected.read_text() == "relative"
