"""Tests for app.connector.registry — MCP connector deduplication."""

from __future__ import annotations

import pytest

pytest.importorskip("mcp")

from pathlib import Path
from unittest.mock import patch

from app.connector.registry import ConnectorRegistry


class TestNormalizeUrl:
    def test_strips_trailing_slash(self):
        assert ConnectorRegistry._normalize_url("https://api.com/") == "https://api.com"

    def test_lowercases_host(self):
        assert ConnectorRegistry._normalize_url("https://API.COM/path") == "https://api.com/path"

    def test_preserves_path(self):
        assert ConnectorRegistry._normalize_url("https://api.com/v1/sse") == "https://api.com/v1/sse"

    def test_handles_no_path(self):
        assert ConnectorRegistry._normalize_url("https://api.com") == "https://api.com"


class TestRegisterFromPlugin:
    def _make_registry(self, tmp_path: Path) -> ConnectorRegistry:
        # Patch catalog loading to avoid missing data file
        with patch.object(ConnectorRegistry, "_load_catalog", return_value={}):
            return ConnectorRegistry(project_dir=str(tmp_path))

    def test_creates_connector(self, tmp_path: Path):
        reg = self._make_registry(tmp_path)
        ids = reg.register_from_plugin("myplugin", {
            "slack": {"url": "https://slack.mcp.io/sse", "type": "remote"},
        })
        assert "slack" in ids
        c = reg.get("slack")
        assert c is not None
        assert c.url == "https://slack.mcp.io/sse"

    def test_dedup_by_url(self, tmp_path: Path):
        reg = self._make_registry(tmp_path)
        reg.register_from_plugin("plugin-a", {
            "slack": {"url": "https://slack.mcp.io/sse", "type": "remote"},
        })
        reg.register_from_plugin("plugin-b", {
            "slack": {"url": "https://slack.mcp.io/sse", "type": "remote"},
        })
        connectors = reg.list_connectors()
        slack_connectors = [c for c in connectors if c.id == "slack"]
        assert len(slack_connectors) == 1
        assert "plugin-a" in slack_connectors[0].referenced_by
        assert "plugin-b" in slack_connectors[0].referenced_by

    def test_strips_namespace(self, tmp_path: Path):
        reg = self._make_registry(tmp_path)
        ids = reg.register_from_plugin("eng", {
            "engineering:slack": {"url": "https://slack.mcp.io/sse", "type": "remote"},
        })
        assert "slack" in ids

    def test_skips_remote_without_url(self, tmp_path: Path):
        reg = self._make_registry(tmp_path)
        ids = reg.register_from_plugin("p", {
            "nourl": {"type": "remote"},
        })
        assert ids == []


class TestRegisterCustom:
    def _make_registry(self, tmp_path: Path) -> ConnectorRegistry:
        with patch.object(ConnectorRegistry, "_load_catalog", return_value={}):
            return ConnectorRegistry(project_dir=str(tmp_path))

    def test_creates_custom_connector(self, tmp_path: Path):
        reg = self._make_registry(tmp_path)
        c = reg.register_custom("my-tool", "My Tool", "https://my.tool/sse")
        assert c.id == "my-tool"
        assert c.source == "custom"

    def test_duplicate_id_raises(self, tmp_path: Path):
        reg = self._make_registry(tmp_path)
        reg.register_custom("my-tool", "My Tool", "https://my.tool/sse")
        with pytest.raises(ValueError):
            reg.register_custom("my-tool", "My Tool 2", "https://my.tool2/sse")


class TestRemoveCustom:
    def _make_registry(self, tmp_path: Path) -> ConnectorRegistry:
        with patch.object(ConnectorRegistry, "_load_catalog", return_value={}):
            return ConnectorRegistry(project_dir=str(tmp_path))

    def test_removes_custom(self, tmp_path: Path):
        reg = self._make_registry(tmp_path)
        reg.register_custom("my-tool", "My Tool", "https://my.tool/sse")
        assert reg.remove_custom("my-tool") is True
        assert reg.get("my-tool") is None

    def test_returns_false_for_builtin(self, tmp_path: Path):
        reg = self._make_registry(tmp_path)
        reg.register_from_plugin("p", {"slack": {"url": "https://s.io", "type": "remote"}})
        assert reg.remove_custom("slack") is False

    def test_returns_false_for_nonexistent(self, tmp_path: Path):
        reg = self._make_registry(tmp_path)
        assert reg.remove_custom("nope") is False


class TestListAndGet:
    def _make_registry(self, tmp_path: Path) -> ConnectorRegistry:
        with patch.object(ConnectorRegistry, "_load_catalog", return_value={}):
            return ConnectorRegistry(project_dir=str(tmp_path))

    def test_list_sorted_by_name(self, tmp_path: Path):
        reg = self._make_registry(tmp_path)
        reg.register_custom("zoom", "Zoom", "https://z.io")
        reg.register_custom("asana", "Asana", "https://a.io")
        reg.register_custom("slack", "Slack", "https://s.io")
        names = [c.name for c in reg.list_connectors()]
        assert names == ["Asana", "Slack", "Zoom"]

    def test_get_existing(self, tmp_path: Path):
        reg = self._make_registry(tmp_path)
        reg.register_custom("my-tool", "My Tool", "https://my.tool/sse")
        assert reg.get("my-tool") is not None

    def test_get_nonexistent(self, tmp_path: Path):
        reg = self._make_registry(tmp_path)
        assert reg.get("nope") is None
