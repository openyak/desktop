"""Tests for app.plugin.converter — plugin data conversion."""

from __future__ import annotations

from pathlib import Path

from app.plugin.converter import convert_mcp_servers, convert_skill, create_plugin_agent
from app.plugin.parser import PluginMcpServer, PluginMeta, PluginSkillRaw


def _make_plugin(**kwargs) -> PluginMeta:
    defaults = {
        "name": "test-plugin",
        "version": "1.0.0",
        "description": "Test plugin",
        "author": "Test",
        "directory": Path("/tmp/test"),
    }
    defaults.update(kwargs)
    return PluginMeta(**defaults)


def _make_raw_skill(**kwargs) -> PluginSkillRaw:
    defaults = {
        "name": "my-skill",
        "description": "A skill",
        "content": "Skill content here.",
        "path": Path("/tmp/test/skills/my-skill/SKILL.md"),
    }
    defaults.update(kwargs)
    return PluginSkillRaw(**defaults)


class TestConvertSkill:
    def test_namespaces_name(self):
        skill = convert_skill(_make_raw_skill(), _make_plugin())
        assert skill.name == "test-plugin:my-skill"

    def test_preserves_content(self):
        raw = _make_raw_skill(content="body text")
        skill = convert_skill(raw, _make_plugin())
        assert skill.content == "body text"
        assert skill.location == str(raw.path)


class TestConvertMcpServers:
    def test_flat_dict_with_remote_type(self):
        servers = [PluginMcpServer(name="slack", url="https://slack.mcp.io/sse")]
        result = convert_mcp_servers(servers, "my-plugin")
        assert "slack" in result
        assert result["slack"]["type"] == "remote"
        assert result["slack"]["url"] == "https://slack.mcp.io/sse"
        assert result["slack"]["enabled"] is False

    def test_empty_list(self):
        assert convert_mcp_servers([], "p") == {}


class TestCreatePluginAgent:
    def test_has_plugin_metadata(self):
        agent = create_plugin_agent(_make_plugin(), ["test-plugin:greeting"])
        assert agent.name == "test-plugin"
        assert agent.mode == "subagent"
        assert agent.metadata.get("plugin") is True

    def test_system_prompt_lists_skills(self):
        skills = ["test-plugin:greet", "test-plugin:farewell"]
        agent = create_plugin_agent(_make_plugin(), skills)
        assert "test-plugin:greet" in agent.system_prompt
        assert "test-plugin:farewell" in agent.system_prompt

    def test_permissions_allow_all(self):
        agent = create_plugin_agent(_make_plugin(), [])
        assert len(agent.permissions.rules) == 1
        assert agent.permissions.rules[0].action == "allow"
        assert agent.permissions.rules[0].permission == "*"
