"""Edit tool tests — single and batch modes."""

from pathlib import Path

import pytest

from app.schemas.agent import AgentInfo
from app.tool.builtin.edit import EditTool
from app.tool.context import ToolContext


def _make_ctx() -> ToolContext:
    return ToolContext(
        session_id="test-session",
        message_id="test-msg",
        agent=AgentInfo(name="test", description="", mode="primary"),
        call_id="test-call",
    )


class TestEditToolSingle:
    """Test single edit mode (old_string + new_string at top level)."""

    @pytest.fixture
    def tool(self):
        return EditTool()

    @pytest.mark.asyncio
    async def test_simple_replacement(self, tool: EditTool, tmp_path: Path):
        f = tmp_path / "test.py"
        f.write_text("def hello():\n    return 'hello'\n")

        result = await tool.execute({
            "file_path": str(f),
            "old_string": "return 'hello'",
            "new_string": "return 'world'",
        }, _make_ctx())

        assert result.success
        assert f.read_text() == "def hello():\n    return 'world'\n"

    @pytest.mark.asyncio
    async def test_nonunique_fails(self, tool: EditTool, tmp_path: Path):
        f = tmp_path / "dup.txt"
        f.write_text("foo\nbar\nfoo\n")

        result = await tool.execute({
            "file_path": str(f),
            "old_string": "foo",
            "new_string": "baz",
        }, _make_ctx())

        assert not result.success
        assert "2 times" in result.error

    @pytest.mark.asyncio
    async def test_replace_all(self, tool: EditTool, tmp_path: Path):
        f = tmp_path / "multi.txt"
        f.write_text("foo\nbar\nfoo\n")

        result = await tool.execute({
            "file_path": str(f),
            "old_string": "foo",
            "new_string": "baz",
            "replace_all": True,
        }, _make_ctx())

        assert result.success
        assert f.read_text() == "baz\nbar\nbaz\n"

    @pytest.mark.asyncio
    async def test_old_string_not_found(self, tool: EditTool, tmp_path: Path):
        f = tmp_path / "miss.txt"
        f.write_text("hello world\n")

        result = await tool.execute({
            "file_path": str(f),
            "old_string": "nonexistent",
            "new_string": "replacement",
        }, _make_ctx())

        assert not result.success
        assert "not found" in result.error.lower()

    @pytest.mark.asyncio
    async def test_same_old_new_fails(self, tool: EditTool, tmp_path: Path):
        f = tmp_path / "same.txt"
        f.write_text("hello\n")

        result = await tool.execute({
            "file_path": str(f),
            "old_string": "hello",
            "new_string": "hello",
        }, _make_ctx())

        assert not result.success
        assert "identical" in result.error.lower()

    @pytest.mark.asyncio
    async def test_returns_diff(self, tool: EditTool, tmp_path: Path):
        f = tmp_path / "diff.txt"
        f.write_text("alpha\nbeta\ngamma\n")

        result = await tool.execute({
            "file_path": str(f),
            "old_string": "beta",
            "new_string": "BETA",
        }, _make_ctx())

        assert result.success
        assert "-beta" in result.output or "- beta" in result.output
        assert "+BETA" in result.output or "+ BETA" in result.output

    @pytest.mark.asyncio
    async def test_missing_new_string(self, tool: EditTool, tmp_path: Path):
        f = tmp_path / "miss_new.txt"
        f.write_text("hello\n")

        result = await tool.execute({
            "file_path": str(f),
            "old_string": "hello",
        }, _make_ctx())

        assert not result.success
        assert "new_string" in result.error


class TestEditToolBatch:
    """Test batch edit mode (edits array)."""

    @pytest.fixture
    def tool(self):
        return EditTool()

    @pytest.mark.asyncio
    async def test_batch_two_edits(self, tool: EditTool, tmp_path: Path):
        f = tmp_path / "batch.py"
        f.write_text("def hello():\n    return 'hello'\n\ndef world():\n    return 'world'\n")

        result = await tool.execute({
            "file_path": str(f),
            "edits": [
                {"old_string": "return 'hello'", "new_string": "return 'hi'"},
                {"old_string": "return 'world'", "new_string": "return 'earth'"},
            ],
        }, _make_ctx())

        assert result.success
        content = f.read_text()
        assert "return 'hi'" in content
        assert "return 'earth'" in content
        assert result.metadata["edits"] == 2

    @pytest.mark.asyncio
    async def test_batch_atomic_rollback(self, tool: EditTool, tmp_path: Path):
        """If second edit fails, file should be unchanged."""
        f = tmp_path / "atomic.txt"
        original = "alpha\nbeta\ngamma\n"
        f.write_text(original)

        result = await tool.execute({
            "file_path": str(f),
            "edits": [
                {"old_string": "beta", "new_string": "BETA"},
                {"old_string": "nonexistent", "new_string": "fail"},
            ],
        }, _make_ctx())

        assert not result.success
        # File was written partially because edits are validated during application.
        # The atomicity is at the write level — if any edit fails mid-batch,
        # the original file is NOT modified (the write happens only after all succeed).
        # Wait, actually looking at the code: the file is written AFTER all edits.
        # So the original should be preserved.
        assert f.read_text() == original

    @pytest.mark.asyncio
    async def test_batch_empty_edits(self, tool: EditTool):
        result = await tool.execute({
            "file_path": "/tmp/whatever.txt",
            "edits": [],
        }, _make_ctx())

        assert not result.success
        assert "no edits" in result.error.lower()

    @pytest.mark.asyncio
    async def test_batch_sequential_dependency(self, tool: EditTool, tmp_path: Path):
        """Second edit depends on first edit's result."""
        f = tmp_path / "seq.txt"
        f.write_text("hello world\n")

        result = await tool.execute({
            "file_path": str(f),
            "edits": [
                {"old_string": "hello", "new_string": "hi"},
                {"old_string": "hi world", "new_string": "hi earth"},
            ],
        }, _make_ctx())

        assert result.success
        assert f.read_text() == "hi earth\n"


class TestEditToolModeValidation:
    """Test that single/batch mode validation works."""

    @pytest.fixture
    def tool(self):
        return EditTool()

    @pytest.mark.asyncio
    async def test_both_modes_fails(self, tool: EditTool):
        result = await tool.execute({
            "file_path": "/tmp/test.txt",
            "old_string": "hello",
            "new_string": "world",
            "edits": [{"old_string": "x", "new_string": "y"}],
        }, _make_ctx())

        assert not result.success
        assert "not both" in result.error.lower()

    @pytest.mark.asyncio
    async def test_neither_mode_fails(self, tool: EditTool):
        result = await tool.execute({
            "file_path": "/tmp/test.txt",
        }, _make_ctx())

        assert not result.success
        assert "old_string" in result.error.lower() or "edits" in result.error.lower()

    def test_tool_id(self, tool: EditTool):
        assert tool.id == "edit"
