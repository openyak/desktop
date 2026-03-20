"""Tests for app.api.config — pure helper functions."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from app.api.config import _mask_key, _remove_env_key, _update_env_file


class TestMaskKey:
    def test_long_key(self):
        result = _mask_key("sk-or-v1-abcdefghijklmnop")
        assert result.startswith("sk-or-v")
        assert result.endswith("mnop")
        assert "..." in result

    def test_short_key(self):
        assert _mask_key("short") == "****"

    def test_boundary_11_chars(self):
        assert _mask_key("12345678901") == "****"  # exactly 11


class TestUpdateEnvFile:
    def test_adds_new_key(self, tmp_path: Path):
        env = tmp_path / ".env"
        with patch("app.api.config._ENV_PATH", env):
            _update_env_file("NEW_KEY", "new_value")
        assert "NEW_KEY=new_value" in env.read_text()

    def test_updates_existing_key(self, tmp_path: Path):
        env = tmp_path / ".env"
        env.write_text("MY_KEY=old\nOTHER=keep\n")
        with patch("app.api.config._ENV_PATH", env):
            _update_env_file("MY_KEY", "new")
        text = env.read_text()
        assert "MY_KEY=new" in text
        assert "OTHER=keep" in text
        assert "old" not in text

    def test_handles_spaces(self, tmp_path: Path):
        env = tmp_path / ".env"
        env.write_text("MY_KEY = old_val\n")
        with patch("app.api.config._ENV_PATH", env):
            _update_env_file("MY_KEY", "new_val")
        assert "MY_KEY=new_val" in env.read_text()


class TestRemoveEnvKey:
    def test_removes_existing(self, tmp_path: Path):
        env = tmp_path / ".env"
        env.write_text("KEY1=val1\nKEY2=val2\n")
        with patch("app.api.config._ENV_PATH", env):
            _remove_env_key("KEY1")
        text = env.read_text()
        assert "KEY1" not in text
        assert "KEY2=val2" in text

    def test_noop_missing_key(self, tmp_path: Path):
        env = tmp_path / ".env"
        env.write_text("OTHER=val\n")
        with patch("app.api.config._ENV_PATH", env):
            _remove_env_key("MISSING")
        assert "OTHER=val" in env.read_text()

    def test_noop_missing_file(self, tmp_path: Path):
        env = tmp_path / ".env"
        with patch("app.api.config._ENV_PATH", env):
            _remove_env_key("KEY")  # should not raise
