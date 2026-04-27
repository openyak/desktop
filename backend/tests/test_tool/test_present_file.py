"""Tests for app.tool.builtin.present_file — explicit file presentation."""

from pathlib import Path

import pytest

from app.schemas.agent import AgentInfo
from app.tool.builtin.present_file import PresentFileTool
from app.tool.context import ToolContext


def ctx(workspace: str | None) -> ToolContext:
    return ToolContext(
        session_id="test-session",
        message_id="test-msg",
        agent=AgentInfo(name="test", description="", mode="primary"),
        call_id="test-call",
        workspace=workspace,
    )


class TestPresentFileTool:
    @pytest.fixture
    def tool(self) -> PresentFileTool:
        return PresentFileTool()

    @pytest.mark.asyncio
    async def test_present_existing_file(self, tool: PresentFileTool, tmp_path: Path):
        path = tmp_path / "report.md"
        path.write_text("# Report\n", encoding="utf-8")

        result = await tool.execute({"file_path": str(path)}, ctx(str(tmp_path)))

        assert result.success
        assert result.metadata["file_path"] == str(path)
        assert result.metadata["title"] == "report.md"
        assert result.title == "Presented report.md"

    @pytest.mark.asyncio
    async def test_present_with_custom_title(self, tool: PresentFileTool, tmp_path: Path):
        path = tmp_path / "report.md"
        path.write_text("# Report\n", encoding="utf-8")

        result = await tool.execute(
            {"file_path": str(path), "title": "Final Report"},
            ctx(str(tmp_path)),
        )

        assert result.success
        assert result.metadata["title"] == "Final Report"
        assert result.title == "Presented Final Report"

    @pytest.mark.asyncio
    async def test_rejects_missing_file(self, tool: PresentFileTool, tmp_path: Path):
        result = await tool.execute({"file_path": "missing.md"}, ctx(str(tmp_path)))

        assert not result.success
        assert result.error == "File not found: missing.md"

    @pytest.mark.asyncio
    async def test_rejects_directory(self, tool: PresentFileTool, tmp_path: Path):
        result = await tool.execute({"file_path": str(tmp_path)}, ctx(str(tmp_path)))

        assert not result.success
        assert result.error == f"Cannot present a directory: {tmp_path}"

    @pytest.mark.asyncio
    async def test_workspace_violation(self, tool: PresentFileTool, tmp_path: Path):
        result = await tool.execute(
            {"file_path": "/etc/passwd"},
            ctx(str(tmp_path)),
        )

        assert not result.success
        assert "outside the workspace directory" in (result.error or "")
