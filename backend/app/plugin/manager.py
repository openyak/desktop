"""Plugin manager — runtime state, enable/disable, persistence."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.plugin.loader import PluginLoadResult, load_plugin, scan_plugins_dir
from app.plugin.parser import PluginMeta
from app.skill.model import SkillInfo
from app.skill.registry import SkillRegistry

logger = logging.getLogger(__name__)


@dataclass
class PluginInfo:
    """Runtime state of a single plugin."""

    name: str
    version: str
    description: str
    author: str
    enabled: bool
    source: str  # "builtin" | "global" | "project"
    skills: list[SkillInfo] = field(default_factory=list)
    connector_ids: list[str] = field(default_factory=list)

    def to_summary(self) -> dict[str, Any]:
        """Serialise for the /plugins/status API response."""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "enabled": self.enabled,
            "source": self.source,
            "skills_count": len(self.skills),
            "mcp_count": len(self.connector_ids),
        }

    def to_detail(self) -> dict[str, Any]:
        """Serialise for the /plugins/{name} API response."""
        return {
            **self.to_summary(),
            "skills": [
                {"name": s.name, "description": s.description}
                for s in self.skills
            ],
            "connector_ids": self.connector_ids,
        }


class PluginManager:
    """Manages plugin lifecycle at runtime.

    Wraps the one-shot ``load_plugins()`` result and adds enable/disable
    with persistence via a JSON file.
    """

    def __init__(
        self,
        skill_registry: SkillRegistry,
        project_dir: str | None = None,
    ) -> None:
        self._skill_registry = skill_registry
        self._project_dir = project_dir
        self._plugins: dict[str, PluginInfo] = {}

        # Load enabled set from disk (plugins are disabled by default)
        self._enabled_path = self._resolve_enabled_path()
        self._enabled: set[str] = self._load_enabled()

    # ------------------------------------------------------------------
    # Bootstrap
    # ------------------------------------------------------------------

    def register_loaded(
        self,
        result: PluginLoadResult,
        source: str,
        meta_map: dict[str, PluginMeta],
        connector_ids_by_plugin: dict[str, list[str]] | None = None,
    ) -> None:
        """Register plugins from a PluginLoadResult into the manager.

        Called during startup after ``load_plugins()`` has done parsing.

        Args:
            connector_ids_by_plugin: mapping of plugin name → list of
                deduplicated connector IDs (provided by ConnectorRegistry).
        """
        # Group skills by plugin name (prefix before colon)
        skills_by_plugin: dict[str, list[SkillInfo]] = {}
        for skill in result.skills:
            plugin_name = skill.name.split(":")[0] if ":" in skill.name else skill.name
            skills_by_plugin.setdefault(plugin_name, []).append(skill)

        cids_map = connector_ids_by_plugin or {}

        # Build PluginInfo for each agent (1 agent = 1 plugin)
        for agent in result.agents:
            meta = meta_map.get(agent.name)
            if not meta:
                continue

            enabled = agent.name in self._enabled
            info = PluginInfo(
                name=agent.name,
                version=meta.version,
                description=meta.description,
                author=meta.author,
                enabled=enabled,
                source=source,
                skills=skills_by_plugin.get(agent.name, []),
                connector_ids=cids_map.get(agent.name, []),
            )
            self._plugins[agent.name] = info

            # If disabled at startup, unregister its skills
            if not enabled:
                for skill in info.skills:
                    self._skill_registry.unregister(skill.name)

    # ------------------------------------------------------------------
    # API
    # ------------------------------------------------------------------

    def status(self) -> dict[str, dict[str, Any]]:
        """All plugins as summary dicts."""
        return {name: p.to_summary() for name, p in self._plugins.items()}

    def detail(self, name: str) -> dict[str, Any] | None:
        """Single plugin detail. Returns None if not found."""
        info = self._plugins.get(name)
        return info.to_detail() if info else None

    def enable(self, name: str) -> bool:
        """Enable a plugin — re-register its skills."""
        info = self._plugins.get(name)
        if not info or info.enabled:
            return False

        for skill in info.skills:
            self._skill_registry.register(skill)

        info.enabled = True
        self._enabled.add(name)
        self._persist_enabled()
        logger.info("Plugin enabled: %s (%d skills)", name, len(info.skills))
        return True

    def disable(self, name: str) -> bool:
        """Disable a plugin — unregister its skills."""
        info = self._plugins.get(name)
        if not info or not info.enabled:
            return False

        for skill in info.skills:
            self._skill_registry.unregister(skill.name)

        info.enabled = False
        self._enabled.discard(name)
        self._persist_enabled()
        logger.info("Plugin disabled: %s (%d skills removed)", name, len(info.skills))
        return True

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _resolve_enabled_path(self) -> Path | None:
        if self._project_dir:
            return Path(self._project_dir).resolve() / ".openyak" / "plugins.enabled.json"
        return Path.home() / ".openyak" / "plugins.enabled.json"

    def _load_enabled(self) -> set[str]:
        if not self._enabled_path or not self._enabled_path.is_file():
            return set()
        try:
            data = json.loads(self._enabled_path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return set(data)
        except (OSError, json.JSONDecodeError):
            pass
        return set()

    def _persist_enabled(self) -> None:
        if not self._enabled_path:
            return
        try:
            self._enabled_path.parent.mkdir(parents=True, exist_ok=True)
            self._enabled_path.write_text(
                json.dumps(sorted(self._enabled), indent=2),
                encoding="utf-8",
            )
        except OSError as e:
            logger.warning("Cannot persist disabled plugins: %s", e)
