"""Plugin loader — scans directories, parses, converts, returns results."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from app.plugin.converter import convert_mcp_servers, convert_skill, create_plugin_agent
from app.plugin.parser import PluginMeta, discover_skills, parse_mcp_json, parse_plugin_json
from app.schemas.agent import AgentInfo
from app.skill.model import SkillInfo

logger = logging.getLogger(__name__)


@dataclass
class PluginLoadResult:
    """Aggregated result of loading one or more plugins."""

    skills: list[SkillInfo] = field(default_factory=list)
    mcp_servers: dict[str, dict] = field(default_factory=dict)
    agents: list[AgentInfo] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    meta_map: dict[str, PluginMeta] = field(default_factory=dict)
    # Per-plugin MCP servers — tracks which plugin owns which servers
    mcp_by_plugin: dict[str, dict[str, dict]] = field(default_factory=dict)

    def merge(self, other: PluginLoadResult) -> None:
        """Merge another result into this one."""
        self.skills.extend(other.skills)
        self.mcp_servers.update(other.mcp_servers)
        self.agents.extend(other.agents)
        self.errors.extend(other.errors)
        self.meta_map.update(other.meta_map)
        self.mcp_by_plugin.update(other.mcp_by_plugin)


def load_plugin(plugin_dir: Path) -> PluginLoadResult:
    """Load a single Claude-format plugin directory.

    Parses plugin.json, discovers skills, parses MCP config, and converts
    everything to OpenYak-compatible objects. All errors are non-fatal.
    """
    result = PluginLoadResult()

    # 1. Parse plugin metadata
    meta = parse_plugin_json(plugin_dir)
    if meta is None:
        result.errors.append(f"Skipping {plugin_dir.name}: no valid .claude-plugin/plugin.json")
        return result

    # 2. Discover and convert skills
    raw_skills = discover_skills(plugin_dir)
    for raw in raw_skills:
        try:
            skill = convert_skill(raw, meta)
            result.skills.append(skill)
        except Exception as e:
            result.errors.append(f"[{meta.name}] skill '{raw.name}': {e}")

    # 3. Parse and convert MCP servers
    remote_servers, local_servers = parse_mcp_json(plugin_dir)
    if remote_servers:
        result.mcp_servers = convert_mcp_servers(remote_servers, meta.name)
    # Local servers (google-workspace, ms365, etc.) use global keys
    # to share a single instance across all plugins
    for local_name, local_config in local_servers.items():
        result.mcp_servers[local_name] = local_config

    # Track per-plugin MCP servers for ConnectorRegistry dedup
    if result.mcp_servers:
        result.mcp_by_plugin[meta.name] = dict(result.mcp_servers)

    # 4. Track metadata
    result.meta_map[meta.name] = meta

    # 5. Create domain agent if plugin has skills
    if result.skills:
        skill_names = [s.name for s in result.skills]
        agent = create_plugin_agent(meta, skill_names)
        result.agents.append(agent)

    logger.debug(
        "Plugin '%s' v%s: %d skills, %d MCP servers",
        meta.name, meta.version, len(result.skills), len(result.mcp_servers),
    )

    return result


def scan_plugins_dir(plugins_dir: Path) -> PluginLoadResult:
    """Scan a directory for plugin subdirectories and load each one."""
    combined = PluginLoadResult()

    if not plugins_dir.is_dir():
        return combined

    for entry in sorted(plugins_dir.iterdir()):
        if not entry.is_dir():
            continue
        # Skip hidden directories (except those containing .claude-plugin)
        if entry.name.startswith("."):
            continue
        plugin_result = load_plugin(entry)
        combined.merge(plugin_result)

    return combined
