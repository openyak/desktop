"""Tests for app.utils.diff — unified diff generation."""

from __future__ import annotations

from app.utils.diff import generate_unified_diff


class TestGenerateUnifiedDiff:
    def test_identical_strings_returns_empty(self):
        assert generate_unified_diff("hello\n", "hello\n") == ""

    def test_single_line_change(self):
        diff = generate_unified_diff("old\n", "new\n", filename="test.py")
        assert "a/test.py" in diff
        assert "b/test.py" in diff
        assert "-old\n" in diff
        assert "+new\n" in diff

    def test_multiline_addition(self):
        diff = generate_unified_diff("line1\n", "line1\nline2\nline3\n")
        assert "+line2\n" in diff
        assert "+line3\n" in diff

    def test_multiline_deletion(self):
        diff = generate_unified_diff("a\nb\nc\n", "a\n")
        assert "-b\n" in diff
        assert "-c\n" in diff

    def test_filename_in_header(self):
        diff = generate_unified_diff("a\n", "b\n", filename="src/main.py")
        assert "a/src/main.py" in diff
        assert "b/src/main.py" in diff

    def test_empty_to_content(self):
        diff = generate_unified_diff("", "hello\n")
        assert "+hello" in diff

    def test_content_to_empty(self):
        diff = generate_unified_diff("hello\n", "")
        assert "-hello" in diff

    def test_no_trailing_newline(self):
        diff = generate_unified_diff("no newline", "with newline\n")
        assert diff  # should produce a diff
