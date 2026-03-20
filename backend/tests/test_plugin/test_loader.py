"""Tests for app.plugin.loader — plugin discovery and loading."""

from __future__ import annotations

import json
from pathlib import Path

from app.plugin.loader import PluginLoadResult, load_plugin, scan_plugins_dir


def _setup_plugin(base: Path, name: str = "my-plugin", *, with_skill: bool = True, with_mcp: bool = False) -> Path:
    """Create a minimal plugin directory structure."""
    plugin_dir = base / name
    cp = plugin_dir / ".claude-plugin"
    cp.mkdir(parents=True)
    (cp / "plugin.json").write_text(json.dumps({
        "name": name,
        "version": "1.0.0",
        "description": f"A test plugin ({name})",
        "author": {"name": "Tester"},
    }))

    if with_skill:
        skill_dir = plugin_dir / "skills" / "greet"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("---\nname: greet\ndescription: Say hi\n---\nHello!")

    if with_mcp:
        (plugin_dir / ".mcp.json").write_text(json.dumps({
            "mcpServers": {"slack": {"url": "https://slack.mcp.io/sse"}}
        }))

    return plugin_dir


class TestPluginLoadResult:
    def test_merge(self):
        a = PluginLoadResult(errors=["err1"])
        b = PluginLoadResult(errors=["err2"])
        a.merge(b)
        assert a.errors == ["err1", "err2"]

    def test_merge_empty(self):
        a = PluginLoadResult()
        b = PluginLoadResult()
        a.merge(b)
        assert a.skills == []
        assert a.errors == []


class TestLoadPlugin:
    def test_valid_plugin_with_skills(self, tmp_path: Path):
        plugin_dir = _setup_plugin(tmp_path)
        result = load_plugin(plugin_dir)
        assert not result.errors
        assert len(result.skills) == 1
        assert result.skills[0].name == "my-plugin:greet"
        assert len(result.agents) == 1

    def test_valid_plugin_with_mcp(self, tmp_path: Path):
        plugin_dir = _setup_plugin(tmp_path, with_mcp=True)
        result = load_plugin(plugin_dir)
        assert "slack" in result.mcp_servers

    def test_missing_plugin_json(self, tmp_path: Path):
        plugin_dir = tmp_path / "empty"
        plugin_dir.mkdir()
        result = load_plugin(plugin_dir)
        assert result.errors
        assert not result.skills

    def test_no_agent_without_skills(self, tmp_path: Path):
        plugin_dir = _setup_plugin(tmp_path, with_skill=False, with_mcp=True)
        result = load_plugin(plugin_dir)
        assert not result.agents  # no agent if no skills


class TestScanPluginsDir:
    def test_scans_subdirectories(self, tmp_path: Path):
        _setup_plugin(tmp_path, "plugin-a")
        _setup_plugin(tmp_path, "plugin-b")
        result = scan_plugins_dir(tmp_path)
        assert len(result.skills) == 2

    def test_skips_hidden_dirs(self, tmp_path: Path):
        _setup_plugin(tmp_path, ".hidden")
        result = scan_plugins_dir(tmp_path)
        assert not result.skills

    def test_nonexistent_dir(self, tmp_path: Path):
        result = scan_plugins_dir(tmp_path / "no-such-dir")
        assert not result.skills
        assert not result.errors
