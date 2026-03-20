"""Glob and Grep tool tests."""

from pathlib import Path

import pytest

from app.schemas.agent import AgentInfo
from app.tool.builtin.glob_tool import GlobTool
from app.tool.builtin.grep import GrepTool
from app.tool.context import ToolContext


def _make_ctx() -> ToolContext:
    return ToolContext(
        session_id="test-session",
        message_id="test-msg",
        agent=AgentInfo(name="test", description="", mode="primary"),
        call_id="test-call",
    )


class TestGlobTool:
    @pytest.fixture
    def tool(self):
        return GlobTool()

    @pytest.mark.asyncio
    async def test_find_py_files(self, tool: GlobTool, tmp_path: Path):
        (tmp_path / "a.py").touch()
        (tmp_path / "b.py").touch()
        (tmp_path / "c.txt").touch()

        result = await tool.execute({
            "pattern": "*.py",
            "path": str(tmp_path),
        }, _make_ctx())

        assert result.success
        assert "a.py" in result.output
        assert "b.py" in result.output
        assert "c.txt" not in result.output

    @pytest.mark.asyncio
    async def test_recursive_glob(self, tool: GlobTool, tmp_path: Path):
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "deep.py").touch()
        (tmp_path / "top.py").touch()

        result = await tool.execute({
            "pattern": "**/*.py",
            "path": str(tmp_path),
        }, _make_ctx())

        assert result.success
        assert "deep.py" in result.output
        assert "top.py" in result.output

    @pytest.mark.asyncio
    async def test_no_matches(self, tool: GlobTool, tmp_path: Path):
        result = await tool.execute({
            "pattern": "*.xyz",
            "path": str(tmp_path),
        }, _make_ctx())

        assert result.success
        assert "no matches" in result.output.lower()


class TestGrepTool:
    @pytest.fixture
    def tool(self):
        return GrepTool()

    @pytest.mark.asyncio
    async def test_find_pattern(self, tool: GrepTool, tmp_path: Path):
        f = tmp_path / "code.py"
        f.write_text("def hello():\n    pass\n\ndef world():\n    pass\n")

        result = await tool.execute({
            "pattern": "def \\w+",
            "path": str(tmp_path),
        }, _make_ctx())

        assert result.success
        assert "def hello" in result.output
        assert "def world" in result.output

    @pytest.mark.asyncio
    async def test_case_insensitive(self, tool: GrepTool, tmp_path: Path):
        f = tmp_path / "test.txt"
        f.write_text("Hello World\nhello world\nHELLO WORLD\n")

        result = await tool.execute({
            "pattern": "hello",
            "path": str(tmp_path),
            "case_insensitive": True,
        }, _make_ctx())

        assert result.success
        assert result.metadata["matches"] == 3

    @pytest.mark.asyncio
    async def test_glob_filter(self, tool: GrepTool, tmp_path: Path):
        (tmp_path / "a.py").write_text("target\n")
        (tmp_path / "b.txt").write_text("target\n")

        result = await tool.execute({
            "pattern": "target",
            "path": str(tmp_path),
            "glob": "*.py",
        }, _make_ctx())

        assert result.success
        assert "a.py" in result.output
        assert "b.txt" not in result.output

    @pytest.mark.asyncio
    async def test_no_matches(self, tool: GrepTool, tmp_path: Path):
        f = tmp_path / "empty.txt"
        f.write_text("nothing here\n")

        result = await tool.execute({
            "pattern": "nonexistent_pattern_xyz",
            "path": str(tmp_path),
        }, _make_ctx())

        assert result.success
        assert "no matches" in result.output.lower()

    @pytest.mark.asyncio
    async def test_with_context(self, tool: GrepTool, tmp_path: Path):
        f = tmp_path / "ctx.txt"
        f.write_text("before\ntarget\nafter\n")

        result = await tool.execute({
            "pattern": "target",
            "path": str(tmp_path),
            "context": 1,
        }, _make_ctx())

        assert result.success
        assert "before" in result.output
        assert "after" in result.output
