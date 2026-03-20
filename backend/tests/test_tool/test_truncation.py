"""Truncation tests — mirrors OpenCode's file-based overflow behavior."""

import os
import tempfile
from pathlib import Path

import pytest

from app.tool.truncation import (
    MAX_BYTES,
    MAX_LINES,
    TruncationResult,
    cleanup_old_outputs,
    truncate_output,
)


@pytest.fixture
def tmp_workspace(tmp_path):
    """Provide a temporary workspace directory."""
    return str(tmp_path)


class TestTruncateOutput:
    """Tests for truncate_output()."""

    def test_short_text_unchanged(self, tmp_workspace):
        text = "short text here"
        result = truncate_output(text, workspace=tmp_workspace)
        assert isinstance(result, TruncationResult)
        assert result.content == text
        assert result.truncated is False
        assert result.output_path is None

    def test_within_line_limit(self, tmp_workspace):
        lines = ["line %d" % i for i in range(MAX_LINES)]
        text = "\n".join(lines)
        result = truncate_output(text, workspace=tmp_workspace)
        assert result.truncated is False

    def test_exceeds_line_limit(self, tmp_workspace):
        lines = ["line %d" % i for i in range(MAX_LINES + 500)]
        text = "\n".join(lines)
        result = truncate_output(text, workspace=tmp_workspace)
        assert result.truncated is True
        assert result.output_path is not None
        assert "truncated" in result.content
        # Full output saved to file
        assert Path(result.output_path).exists()
        saved = Path(result.output_path).read_text(encoding="utf-8")
        assert saved == text

    def test_exceeds_byte_limit(self, tmp_workspace):
        # Each line ~100 bytes, 600 lines = ~60KB > 50KB limit
        text = "\n".join(["x" * 100 for _ in range(600)])
        result = truncate_output(text, workspace=tmp_workspace)
        assert result.truncated is True
        assert "bytes" in result.content or "truncated" in result.content
        assert Path(result.output_path).exists()

    def test_head_direction(self, tmp_workspace):
        lines = ["line %d" % i for i in range(MAX_LINES + 100)]
        text = "\n".join(lines)
        result = truncate_output(text, workspace=tmp_workspace, direction="head")
        assert result.truncated is True
        # Preview should contain early lines
        assert "line 0" in result.content
        assert "line 1" in result.content

    def test_tail_direction(self, tmp_workspace):
        lines = ["line %d" % i for i in range(MAX_LINES + 100)]
        text = "\n".join(lines)
        result = truncate_output(text, workspace=tmp_workspace, direction="tail")
        assert result.truncated is True
        # Preview should contain late lines
        last = MAX_LINES + 100 - 1
        assert f"line {last}" in result.content

    def test_hint_with_task_tool(self, tmp_workspace):
        text = "\n".join(["line" for _ in range(MAX_LINES + 10)])
        result = truncate_output(text, workspace=tmp_workspace, has_task_tool=True)
        assert result.truncated is True
        assert "Task tool" in result.content
        assert "delegate" in result.content

    def test_hint_without_task_tool(self, tmp_workspace):
        text = "\n".join(["line" for _ in range(MAX_LINES + 10)])
        result = truncate_output(text, workspace=tmp_workspace, has_task_tool=False)
        assert result.truncated is True
        assert "Grep" in result.content

    def test_custom_limits(self, tmp_workspace):
        text = "a\nb\nc\nd\ne\nf"
        result = truncate_output(text, workspace=tmp_workspace, max_lines=3)
        assert result.truncated is True
        assert result.output_path is not None

    def test_output_dir_created(self, tmp_workspace):
        text = "\n".join(["line" for _ in range(MAX_LINES + 10)])
        result = truncate_output(text, workspace=tmp_workspace)
        output_dir = Path(tmp_workspace) / ".openyak" / "tool-output"
        assert output_dir.exists()
        assert result.output_path is not None

    def test_empty_text(self, tmp_workspace):
        result = truncate_output("", workspace=tmp_workspace)
        assert result.truncated is False
        assert result.content == ""

    def test_exactly_at_line_limit(self, tmp_workspace):
        lines = ["line %d" % i for i in range(MAX_LINES)]
        text = "\n".join(lines)
        result = truncate_output(text, workspace=tmp_workspace)
        assert result.truncated is False


class TestCleanup:
    """Tests for cleanup_old_outputs()."""

    def test_cleanup_removes_old_files(self, tmp_workspace):
        output_dir = Path(tmp_workspace) / ".openyak" / "tool-output"
        output_dir.mkdir(parents=True, exist_ok=True)
        # Create a file and backdate it
        old_file = output_dir / "old.txt"
        old_file.write_text("old data")
        # Set mtime to 8 days ago
        import time
        old_time = time.time() - (8 * 24 * 3600)
        os.utime(old_file, (old_time, old_time))

        new_file = output_dir / "new.txt"
        new_file.write_text("new data")

        removed = cleanup_old_outputs(workspace=tmp_workspace)
        assert removed == 1
        assert not old_file.exists()
        assert new_file.exists()

    def test_cleanup_no_dir(self, tmp_workspace):
        # Non-existent dir should not error
        removed = cleanup_old_outputs(workspace=str(Path(tmp_workspace) / "nonexistent"))
        assert removed == 0
