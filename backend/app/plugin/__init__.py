"""Plugin system — load Claude knowledge-work-plugins into OpenYak.

Bundled plugins ship with the backend in ``app/data/plugins/``.
Users can add more in ``.openyak/plugins/`` (project-level) or
``~/.openyak/plugins/`` (global) — later sources override earlier ones.
"""

from __future__ import annotations

import logging
from pathlib import Path

from app.plugin.loader import PluginLoadResult, scan_plugins_dir

logger = logging.getLogger(__name__)

# Bundled plugins shipped with the application.
_BUNDLED_PLUGINS_DIR = Path(__file__).resolve().parent.parent / "data" / "plugins"


def load_plugins(project_dir: str | None = None) -> PluginLoadResult:
    """Scan for Claude-format plugins and convert them to OpenYak objects.

    Search order (lowest → highest priority):
      1. Bundled plugins:  app/data/plugins/
      2. Global plugins:   ~/.openyak/plugins/
      3. Project plugins:  {project_dir}/.openyak/plugins/
    """
    combined = PluginLoadResult()

    # 1. Bundled plugins (shipped with the app)
    if _BUNDLED_PLUGINS_DIR.is_dir():
        combined.merge(scan_plugins_dir(_BUNDLED_PLUGINS_DIR))

    # 2. Global user plugins
    global_dir = Path.home() / ".openyak" / "plugins"
    if global_dir.is_dir():
        combined.merge(scan_plugins_dir(global_dir))

    # 3. Project-level plugins
    if project_dir:
        project_plugins = Path(project_dir).resolve() / ".openyak" / "plugins"
        if project_plugins.is_dir():
            combined.merge(scan_plugins_dir(project_plugins))

    if combined.skills or combined.mcp_servers:
        logger.info(
            "Plugins loaded: %d skills, %d MCP servers, %d agents",
            len(combined.skills),
            len(combined.mcp_servers),
            len(combined.agents),
        )

    return combined


def load_plugins_by_source(
    project_dir: str | None = None,
) -> list[tuple[str, PluginLoadResult]]:
    """Load plugins from each source separately for PluginManager tracking.

    Returns list of (source_label, result) tuples.
    """
    sources: list[tuple[str, PluginLoadResult]] = []

    if _BUNDLED_PLUGINS_DIR.is_dir():
        r = scan_plugins_dir(_BUNDLED_PLUGINS_DIR)
        if r.skills or r.agents:
            sources.append(("builtin", r))

    global_dir = Path.home() / ".openyak" / "plugins"
    if global_dir.is_dir():
        r = scan_plugins_dir(global_dir)
        if r.skills or r.agents:
            sources.append(("global", r))

    if project_dir:
        project_plugins = Path(project_dir).resolve() / ".openyak" / "plugins"
        if project_plugins.is_dir():
            r = scan_plugins_dir(project_plugins)
            if r.skills or r.agents:
                sources.append(("project", r))

    return sources
