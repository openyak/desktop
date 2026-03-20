"""Tests for app.tool.builtin.todo — TodoTool._build_result()."""

from __future__ import annotations

from app.tool.builtin.todo import TodoTool


class TestBuildResult:
    def test_summary_counts(self):
        todos = [
            {"content": "A", "status": "completed"},
            {"content": "B", "status": "in_progress"},
            {"content": "C", "status": "pending"},
        ]
        result = TodoTool._build_result(todos)
        assert "1/3 done" in result.output
        assert "1 in progress" in result.output
        assert "1 pending" in result.output

    def test_all_completed(self):
        todos = [
            {"content": "A", "status": "completed"},
            {"content": "B", "status": "completed"},
        ]
        result = TodoTool._build_result(todos)
        assert "2/2 done" in result.output
        assert "pending" not in result.output

    def test_empty_list(self):
        result = TodoTool._build_result([])
        assert "0/0 done" in result.output
