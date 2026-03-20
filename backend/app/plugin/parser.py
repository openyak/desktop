"""Parse Claude knowledge-work-plugin directories.

Handles .claude-plugin/plugin.json, .mcp.json, and skills/*/SKILL.md files.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)


@dataclass
class PluginMeta:
    """Metadata from .claude-plugin/plugin.json."""

    name: str
    version: str
    description: str
    author: str
    directory: Path


@dataclass
class PluginSkillRaw:
    """A raw skill discovered from skills/*/SKILL.md."""

    name: str  # From frontmatter or directory name
    description: str  # From frontmatter or extracted from content
    content: str  # Markdown body (after frontmatter)
    path: Path


@dataclass
class PluginMcpServer:
    """An MCP server entry from .mcp.json."""

    name: str
    url: str


def parse_plugin_json(plugin_dir: Path) -> PluginMeta | None:
    """Parse .claude-plugin/plugin.json and return PluginMeta.

    Returns None if the file is missing, malformed, or lacks required fields.
    """
    path = plugin_dir / ".claude-plugin" / "plugin.json"
    if not path.is_file():
        return None

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        logger.warning("Cannot parse %s: %s", path, e)
        return None

    name = data.get("name")
    version = data.get("version", "0.0.0")
    description = data.get("description", "")
    author = data.get("author", {}).get("name", "Unknown")

    if not name or not isinstance(name, str):
        logger.warning("Missing 'name' in %s", path)
        return None

    return PluginMeta(
        name=name,
        version=version,
        description=description,
        author=author,
        directory=plugin_dir,
    )


def parse_mcp_json(plugin_dir: Path) -> tuple[list[PluginMcpServer], dict[str, dict]]:
    """Parse .mcp.json and return MCP server entries.

    Returns:
        (remote_servers, local_servers_raw)
        - remote_servers: list of PluginMcpServer with URL
        - local_servers_raw: dict of name→config for local stdio servers
    """
    path = plugin_dir / ".mcp.json"
    if not path.is_file():
        return [], {}

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        logger.warning("Cannot parse %s: %s", path, e)
        return [], {}

    servers_dict = data.get("mcpServers", {})
    if not isinstance(servers_dict, dict):
        return [], {}

    remote_servers: list[PluginMcpServer] = []
    local_servers: dict[str, dict] = {}

    for name, config in servers_dict.items():
        if not isinstance(config, dict):
            continue

        server_type = config.get("type", "http")

        if server_type == "local":
            # Local stdio server (e.g. google-workspace, ms365)
            command = config.get("command", [])
            if command:
                local_servers[name] = {
                    "type": "local",
                    "command": command,
                    "enabled": config.get("enabled", False),
                }
                env = config.get("environment")
                if env:
                    local_servers[name]["environment"] = env
        else:
            # Remote HTTP server
            url = config.get("url", "")
            if not url:
                continue
            remote_servers.append(PluginMcpServer(name=name, url=url))

    return remote_servers, local_servers


def _split_frontmatter(text: str) -> tuple[dict | None, str]:
    """Split YAML frontmatter from markdown body.

    Returns (parsed_dict_or_None, body_string).
    """
    if not text.startswith("---"):
        return None, text

    end = text.find("\n---", 3)
    if end == -1:
        return None, text

    fm_str = text[3:end].strip()
    body = text[end + 4:].strip()

    try:
        data = yaml.safe_load(fm_str)
    except yaml.YAMLError:
        return None, text

    if isinstance(data, dict):
        return data, body
    return None, text


def discover_skills(plugin_dir: Path) -> list[PluginSkillRaw]:
    """Find all skills/*/SKILL.md files in a plugin directory.

    Parses YAML frontmatter if present to extract name/description.
    Falls back to directory name and first-paragraph extraction.
    """
    skills_dir = plugin_dir / "skills"
    if not skills_dir.is_dir():
        return []

    skills: list[PluginSkillRaw] = []
    for skill_path in sorted(skills_dir.rglob("SKILL.md")):
        try:
            raw_text = skill_path.read_text(encoding="utf-8")
        except OSError as e:
            logger.debug("Cannot read %s: %s", skill_path, e)
            continue

        fm, body = _split_frontmatter(raw_text)

        # Name: frontmatter > directory name
        skill_name = (fm.get("name") if fm else None) or skill_path.parent.name

        # Description: frontmatter > extracted from body
        skill_desc = (fm.get("description") if fm else None) or extract_description(body)

        skills.append(PluginSkillRaw(
            name=skill_name,
            description=skill_desc,
            content=body if fm else raw_text,
            path=skill_path,
        ))

    return skills


def extract_description(markdown: str) -> str:
    """Extract the first non-heading, non-empty paragraph as a description."""
    for line in markdown.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            continue
        if stripped.startswith("```"):
            break
        # Found a content line — take it as description
        # Strip markdown formatting
        desc = re.sub(r"\*\*|__|\*|_|`", "", stripped)
        # Truncate to reasonable length
        if len(desc) > 200:
            desc = desc[:197] + "..."
        return desc

    return "Plugin skill"
