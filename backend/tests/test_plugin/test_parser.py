"""Tests for app.plugin.parser — plugin JSON, MCP JSON, SKILL.md parsing."""

from __future__ import annotations

import json
from pathlib import Path

from app.plugin.parser import (
    PluginMcpServer,
    _split_frontmatter,
    discover_skills,
    extract_description,
    parse_mcp_json,
    parse_plugin_json,
)


def _write_plugin_json(plugin_dir: Path, data: dict) -> None:
    cp = plugin_dir / ".claude-plugin"
    cp.mkdir(parents=True, exist_ok=True)
    (cp / "plugin.json").write_text(json.dumps(data))


class TestParsePluginJson:
    def test_valid(self, tmp_path: Path):
        _write_plugin_json(tmp_path, {
            "name": "my-plugin",
            "version": "1.2.3",
            "description": "A plugin",
            "author": {"name": "Alice"},
        })
        meta = parse_plugin_json(tmp_path)
        assert meta is not None
        assert meta.name == "my-plugin"
        assert meta.version == "1.2.3"
        assert meta.author == "Alice"

    def test_missing_file_returns_none(self, tmp_path: Path):
        assert parse_plugin_json(tmp_path) is None

    def test_missing_name_returns_none(self, tmp_path: Path):
        _write_plugin_json(tmp_path, {"version": "1.0"})
        assert parse_plugin_json(tmp_path) is None

    def test_malformed_json_returns_none(self, tmp_path: Path):
        cp = tmp_path / ".claude-plugin"
        cp.mkdir(parents=True)
        (cp / "plugin.json").write_text("{bad json!!!")
        assert parse_plugin_json(tmp_path) is None

    def test_defaults_for_optional_fields(self, tmp_path: Path):
        _write_plugin_json(tmp_path, {"name": "minimal"})
        meta = parse_plugin_json(tmp_path)
        assert meta is not None
        assert meta.version == "0.0.0"
        assert meta.author == "Unknown"
        assert meta.description == ""


class TestParseMcpJson:
    def test_remote_servers(self, tmp_path: Path):
        data = {"mcpServers": {"slack": {"url": "https://slack.mcp.io/sse"}}}
        (tmp_path / ".mcp.json").write_text(json.dumps(data))
        remote, local = parse_mcp_json(tmp_path)
        assert len(remote) == 1
        assert remote[0].name == "slack"
        assert remote[0].url == "https://slack.mcp.io/sse"
        assert not local

    def test_local_servers(self, tmp_path: Path):
        data = {"mcpServers": {"gdrive": {
            "type": "local",
            "command": ["python", "-m", "gdrive"],
            "environment": {"GOOGLE_KEY": "xxx"},
        }}}
        (tmp_path / ".mcp.json").write_text(json.dumps(data))
        remote, local = parse_mcp_json(tmp_path)
        assert not remote
        assert "gdrive" in local
        assert local["gdrive"]["command"] == ["python", "-m", "gdrive"]
        assert local["gdrive"]["environment"] == {"GOOGLE_KEY": "xxx"}

    def test_missing_file_returns_empty(self, tmp_path: Path):
        remote, local = parse_mcp_json(tmp_path)
        assert remote == []
        assert local == {}

    def test_server_without_url_skipped(self, tmp_path: Path):
        data = {"mcpServers": {"nourl": {"type": "http"}}}
        (tmp_path / ".mcp.json").write_text(json.dumps(data))
        remote, local = parse_mcp_json(tmp_path)
        assert not remote

    def test_mixed(self, tmp_path: Path):
        data = {"mcpServers": {
            "slack": {"url": "https://slack.mcp.io/sse"},
            "gdrive": {"type": "local", "command": ["gdrive-server"]},
        }}
        (tmp_path / ".mcp.json").write_text(json.dumps(data))
        remote, local = parse_mcp_json(tmp_path)
        assert len(remote) == 1
        assert len(local) == 1


class TestSplitFrontmatter:
    def test_valid(self):
        fm, body = _split_frontmatter("---\nname: foo\n---\nbody text")
        assert fm == {"name": "foo"}
        assert body == "body text"

    def test_no_frontmatter(self):
        fm, body = _split_frontmatter("just text")
        assert fm is None
        assert body == "just text"

    def test_unclosed(self):
        fm, body = _split_frontmatter("---\nname: foo\nno closing")
        assert fm is None

    def test_non_dict_returns_none(self):
        fm, body = _split_frontmatter("---\n- item1\n- item2\n---\nbody")
        assert fm is None

    def test_invalid_yaml(self):
        fm, body = _split_frontmatter("---\n: : invalid\n---\nbody")
        assert fm is None


class TestDiscoverSkills:
    def test_finds_skill_files(self, tmp_path: Path):
        skill_dir = tmp_path / "skills" / "greeting"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("---\nname: greet\ndescription: Say hi\n---\nHello!")
        skills = discover_skills(tmp_path)
        assert len(skills) == 1
        assert skills[0].name == "greet"
        assert skills[0].description == "Say hi"

    def test_falls_back_to_dir_name(self, tmp_path: Path):
        skill_dir = tmp_path / "skills" / "my-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("No frontmatter here, just content.")
        skills = discover_skills(tmp_path)
        assert len(skills) == 1
        assert skills[0].name == "my-skill"

    def test_no_skills_dir(self, tmp_path: Path):
        assert discover_skills(tmp_path) == []


class TestExtractDescription:
    def test_first_paragraph(self):
        md = "# Title\n\nThis is the description.\n\nMore text."
        assert extract_description(md) == "This is the description."

    def test_strips_markdown(self):
        md = "**bold** and *italic* and `code`"
        assert extract_description(md) == "bold and italic and code"

    def test_truncates_at_200(self):
        md = "a" * 300
        result = extract_description(md)
        assert len(result) == 200
        assert result.endswith("...")

    def test_stops_at_code_block(self):
        md = "# Title\n```python\ncode\n```"
        assert extract_description(md) == "Plugin skill"

    def test_all_headings(self):
        md = "# H1\n## H2\n### H3"
        assert extract_description(md) == "Plugin skill"
