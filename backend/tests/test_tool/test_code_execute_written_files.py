"""Tests for code_execute written file tracking."""

from pathlib import Path

import pytest

from app.schemas.agent import AgentInfo
from app.tool.builtin.code_execute import CodeExecuteTool
from app.tool.context import ToolContext


def _make_ctx(workspace: str | None = None) -> ToolContext:
    return ToolContext(
        session_id="test-session",
        message_id="test-msg",
        agent=AgentInfo(name="test", description="", mode="primary"),
        call_id="test-call",
        workspace=workspace,
    )


@pytest.mark.asyncio
async def test_tracks_written_files_without_workspace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.chdir(tmp_path)
    tool = CodeExecuteTool()

    result = await tool.execute(
        {"code": "from pathlib import Path\nPath('deliverable.md').write_text('ok')"},
        _make_ctx(),
    )

    assert result.success
    assert result.metadata["written_files"] == [str((tmp_path / "deliverable.md").resolve())]


@pytest.mark.asyncio
async def test_tracks_written_files_inside_workspace(tmp_path: Path):
    tool = CodeExecuteTool()

    result = await tool.execute(
        {
            "code": (
                "from pathlib import Path\n"
                f"Path({str(tmp_path / 'report.md')!r}).write_text('ok')"
            )
        },
        _make_ctx(str(tmp_path)),
    )

    assert result.success
    assert result.metadata["written_files"] == [str((tmp_path / "report.md").resolve())]
