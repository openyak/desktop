"""System prompt builder.

Assembles the full system prompt from:
  - Agent's base prompt template
  - Environment info (cwd, platform, date)
  - Project instructions (if any)

Supports prompt caching: static sections (agent base prompt, project instructions)
are separated from dynamic sections (environment info, workspace memory, skills)
so that Anthropic API prompt caching can be applied to the static portion.
"""

from __future__ import annotations

import os
import platform
import time as _time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from app.schemas.agent import AgentInfo


@dataclass(frozen=True)
class SystemPromptParts:
    """System prompt split into cached (static) and dynamic sections.

    The cached portion (agent base prompt + project instructions) is stable
    across turns and can benefit from Anthropic's prompt caching.
    The dynamic portion (environment info, workspace memory, skills) changes
    each turn and should not be cached.
    """

    cached: str
    dynamic: str

    def as_plain_text(self) -> str:
        """Join both parts into a single string (for non-caching providers)."""
        parts = [p for p in (self.cached, self.dynamic) if p]
        return "\n\n".join(parts)

    def as_cached_blocks(self) -> list[dict[str, Any]]:
        """Format as Anthropic system message blocks with cache_control.

        Returns a list suitable for the Anthropic API ``system`` parameter:
        the cached block gets a ``cache_control`` marker so it is stored
        server-side and reused across turns within the same session.
        """
        blocks: list[dict[str, Any]] = []
        if self.cached:
            blocks.append({
                "type": "text",
                "text": self.cached,
                "cache_control": {"type": "ephemeral"},
            })
        if self.dynamic:
            blocks.append({
                "type": "text",
                "text": self.dynamic,
            })
        return blocks


def build_system_prompt(
    agent: AgentInfo,
    *,
    directory: str | None = None,
    workspace: str | None = None,
    fts_status: dict | None = None,
    workspace_memory_section: str | None = None,
) -> SystemPromptParts:
    """Build the complete system prompt for an LLM call.

    Returns a ``SystemPromptParts`` with cached (static) and dynamic sections
    separated so callers can apply prompt caching when the provider supports it.
    """
    # --- Cached (static) sections ---
    cached_parts: list[str] = []

    # Agent's base prompt (stable across turns)
    if agent.system_prompt:
        cached_parts.append(agent.system_prompt)

    # Project instructions (stable across turns)
    project_instructions = _load_project_instructions(directory)
    if project_instructions:
        cached_parts.append(project_instructions)

    # --- Dynamic sections (change each turn) ---
    dynamic_parts: list[str] = []

    # Workspace-scoped memory
    if workspace_memory_section:
        dynamic_parts.append(workspace_memory_section)

    skills_info = _skills_awareness_section()
    if skills_info:
        dynamic_parts.append(skills_info)

    # Environment info (timestamp changes every minute)
    env_info = _environment_section(directory, workspace=workspace, fts_status=fts_status)
    dynamic_parts.append(env_info)

    return SystemPromptParts(
        cached="\n\n".join(cached_parts),
        dynamic="\n\n".join(dynamic_parts),
    )


def _environment_section(directory: str | None = None, *, workspace: str | None = None, fts_status: dict | None = None) -> str:
    """Generate environment context section."""
    cwd = directory or os.getcwd()
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    current_time = now.strftime("%H:%M")
    tz_name = _time.tzname[_time.daylight] if _time.daylight else _time.tzname[0]
    plat = platform.system()

    section = f"""# Environment
- Working directory: {cwd}
- Platform: {plat}
- Current date: {today} ({current_time} {tz_name})
- Current year: {now.year}"""

    if workspace:
        output_dir = str(Path(workspace) / "openyak_written")
        section += f"""

# Workspace Restriction
You are restricted to the following workspace directory: {workspace}
All file operations (read, write, edit, glob, grep) and shell command working directories \
MUST stay within this directory. Attempting to access paths outside will be blocked.
Always use paths relative to or inside: {workspace}

# Default Output Directory
When creating new files and the user does not specify a location, \
place them in: {output_dir}
This directory is auto-created for you. Use it to keep generated files organized.
If the user explicitly specifies a different path (within the workspace), use that instead."""
    else:
        section += f"""

# File Reference Format
You are not restricted to a workspace for this session.
When referencing local files in your response, prefer absolute paths rooted from the working directory: {cwd}
Do not return relative paths like `src/main.py` when an absolute path is available."""

    if fts_status:
        status = fts_status.get("status", "unknown")
        file_count = fts_status.get("file_count")
        count_str = f" ({file_count:,} files)" if file_count else ""
        if status == "indexed":
            section += f"""

# Full-Text Search
- FTS: enabled, workspace indexed{count_str}
- Full-text search available via `search` tool — use it for broad keyword discovery
- Use `grep` for exact regex pattern matching"""
        elif status == "indexing":
            section += """

# Full-Text Search
- FTS: enabled, workspace indexing in progress
- Full-text `search` tool will be available once indexing completes"""

    return section


def _load_project_instructions(directory: str | None) -> str | None:
    """Load project-specific instructions from conventional locations."""
    if not directory:
        return None

    # Check common instruction file locations
    candidates = [
        os.path.join(directory, "AGENTS.md"),
        os.path.join(directory, ".openyak", "instructions.md"),
        os.path.join(directory, ".openyak", "instructions"),
    ]

    for path in candidates:
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                if content:
                    return f"# Project Instructions\n{content}"
            except OSError:
                continue

    return None


def _skills_awareness_section() -> str | None:
    """Return a compact summary of currently enabled skills.

    This intentionally duplicates a small amount of information from the skill
    tool description because many models route better when relevant capabilities
    are surfaced in the system prompt itself.
    """
    try:
        from app.dependencies import get_skill_registry

        registry = get_skill_registry()
        active = sorted(registry.active_skills(), key=lambda s: s.name.lower())
    except Exception:
        return None

    if not active:
        return None

    shown = active[:12]
    remaining = len(active) - len(shown)

    lines = [
        "# Skill Routing",
        "If the task matches one of the skills below, call the `skill` tool before major work.",
        "Use skills for specialised workflows or output-generation tasks. Do not load a skill just to read a file.",
        "",
        "Currently available skills:",
    ]

    for skill in shown:
        desc = (skill.description or "").strip()
        if len(desc) > 90:
            desc = desc[:87] + "..."
        lines.append(f"- {skill.name}: {desc}")

    if remaining > 0:
        lines.append(f"- (and {remaining} more available via the `skill` tool)")

    return "\n".join(lines)



# _skills_section removed — skill listing now lives only in SkillTool.description
# to avoid token duplication. See app/tool/builtin/skill.py.
