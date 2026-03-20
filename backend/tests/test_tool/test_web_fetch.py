"""Tests for app.tool.builtin.web_fetch — HTML stripping."""

from __future__ import annotations

from app.tool.builtin.web_fetch import _strip_html


class TestStripHtml:
    def test_removes_script_tags(self):
        html = '<p>hello</p><script>alert("xss")</script><p>world</p>'
        result = _strip_html(html)
        assert "alert" not in result
        assert "hello" in result
        assert "world" in result

    def test_removes_style_tags(self):
        html = "<style>body{color:red}</style><p>text</p>"
        result = _strip_html(html)
        assert "color" not in result
        assert "text" in result

    def test_removes_html_tags(self):
        html = "<div><p>hello</p></div>"
        result = _strip_html(html)
        assert "hello" in result
        assert "<" not in result

    def test_collapses_whitespace(self):
        html = "<p>hello</p>   \n\n   <p>world</p>"
        result = _strip_html(html)
        # Multiple spaces should be collapsed
        assert "  " not in result

    def test_nested_tags(self):
        html = "<div><span><b>nested</b></span></div>"
        result = _strip_html(html)
        assert "nested" in result
        assert "<" not in result
