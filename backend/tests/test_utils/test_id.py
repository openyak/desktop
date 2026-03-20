"""Tests for app.utils.id — ULID generation."""

from __future__ import annotations

from app.utils.id import generate_ulid


class TestGenerateUlid:
    def test_returns_string(self):
        assert isinstance(generate_ulid(), str)

    def test_uniqueness(self):
        ids = [generate_ulid() for _ in range(100)]
        assert len(set(ids)) == 100

    def test_length_26(self):
        assert len(generate_ulid()) == 26
