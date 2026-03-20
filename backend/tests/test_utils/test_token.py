"""Tests for app.utils.token — token counting utilities."""

from __future__ import annotations

import pytest

from app.utils.token import count_tokens, estimate_tokens


class TestCountTokens:
    @pytest.mark.skipif(True, reason="tiktoken needs network to download encoding data")
    def test_empty_string_returns_zero(self):
        assert count_tokens("") == 0

    @pytest.mark.skipif(True, reason="tiktoken needs network to download encoding data")
    def test_known_text(self):
        result = count_tokens("hello world")
        assert isinstance(result, int)
        assert result > 0

    @pytest.mark.skipif(True, reason="tiktoken needs network to download encoding data")
    def test_unicode_text(self):
        # CJK characters should not crash
        result = count_tokens("你好世界")
        assert result > 0

    @pytest.mark.skipif(True, reason="tiktoken needs network to download encoding data")
    def test_long_text(self):
        result = count_tokens("a " * 500)
        assert result > 0


class TestEstimateTokens:
    def test_empty_string_returns_one(self):
        assert estimate_tokens("") == 1

    def test_short_string(self):
        assert estimate_tokens("abc") == 1  # 3 // 4 = 0, clamped to 1

    def test_proportional(self):
        assert estimate_tokens("a" * 100) == 25
