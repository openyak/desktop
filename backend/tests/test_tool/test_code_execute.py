"""Tests for app.tool.builtin.code_execute — blocked import checking."""

from __future__ import annotations

from app.tool.builtin.code_execute import _check_blocked_imports


class TestBlockedImports:
    def test_subprocess_blocked(self):
        assert _check_blocked_imports("import subprocess") is not None

    def test_shutil_blocked(self):
        assert _check_blocked_imports("import shutil") is not None

    def test_socket_blocked(self):
        assert _check_blocked_imports("import socket") is not None

    def test_submodule_blocked(self):
        assert _check_blocked_imports("from http.server import HTTPServer") is not None

    def test_allowed_import(self):
        assert _check_blocked_imports("import pandas") is None

    def test_indented_import_blocked(self):
        assert _check_blocked_imports("    import subprocess") is not None

    def test_from_import_blocked(self):
        assert _check_blocked_imports("from subprocess import run") is not None

    def test_comment_not_blocked(self):
        assert _check_blocked_imports("# import subprocess") is None
