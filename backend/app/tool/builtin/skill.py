"""Skill tool — lets agents load specialised instruction sets on demand."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from app.tool.base import ToolDefinition, ToolResult
from app.tool.context import ToolContext


class SkillTool(ToolDefinition):
    """Meta-tool that loads SKILL.md instruction sets into the conversation.

    The tool description dynamically lists all available skills so the LLM
    knows what it can invoke.
    """

    def __init__(self, skill_registry: "SkillRegistry | None" = None) -> None:
        self._skill_registry = skill_registry

    # ------------------------------------------------------------------
    # ToolDefinition interface
    # ------------------------------------------------------------------

    @property
    def id(self) -> str:
        return "skill"

    @property
    def description(self) -> str:
        """Dynamically generated — includes list of available skills."""
        base = (
            "Load a specialised skill that provides domain-specific "
            "instructions and workflows.\n\n"
            "When you recognise that a task matches one of the available "
            "skills listed below, use this tool to load the full skill "
            "instructions. The skill will inject detailed instructions, "
            "workflows, and access to bundled resources (scripts, references, "
            "templates) into the conversation context.\n\n"
            'Tool output includes a `<skill_content name="...">` block with '
            "the loaded content and a `<skill_files>` block listing bundled "
            "resource files that you can read with the `read` tool.\n\n"
            "Invoke this tool to load a skill when a task matches one of "
            "the available skills listed below:"
        )

        if not self._skill_registry or self._skill_registry.count == 0:
            return base + "\n\nNo skills are currently available."

        lines = [base, "", "<available_skills>"]
        for skill in self._skill_registry.all_skills():
            lines.append("  <skill>")
            lines.append(f"    <name>{skill.name}</name>")
            lines.append(f"    <description>{skill.description}</description>")
            lines.append("  </skill>")
        lines.append("</available_skills>")
        return "\n".join(lines)

    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "The name of the skill to load (from available_skills).",
                },
            },
            "required": ["name"],
        }

    async def execute(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        name: str = args["name"]

        if not self._skill_registry:
            return ToolResult(error="Skill system is not initialised.")

        skill = self._skill_registry.get(name)
        if skill is None:
            available = ", ".join(self._skill_registry.skill_names()) or "none"
            return ToolResult(
                error=f'Skill "{name}" not found. Available skills: {available}',
            )

        # Collect bundled files in the same directory (up to 10)
        skill_dir = Path(skill.location).parent
        bundled_files = _list_bundled_files(skill_dir, limit=10)

        files_block = ""
        if bundled_files:
            file_tags = "\n".join(f"<file>{f}</file>" for f in bundled_files)
            files_block = (
                f"\n\n<skill_files>\n{file_tags}\n</skill_files>"
            )

        base_dir_hint = (
            f"\n\nBase directory for this skill: {skill_dir}\n"
            "Relative paths in this skill (e.g., scripts/, reference/) "
            "are relative to this base directory."
        )

        output = (
            f'<skill_content name="{skill.name}">\n'
            f"# Skill: {skill.name}\n\n"
            f"{skill.content.strip()}\n"
            f"{base_dir_hint}\n"
            f"{files_block}\n"
            f"</skill_content>"
        )

        ctx.publish_metadata(title=f"Loaded skill: {skill.name}")
        return ToolResult(
            output=output,
            title=f"Loaded skill: {skill.name}",
            metadata={"name": skill.name, "dir": str(skill_dir)},
        )


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _list_bundled_files(directory: Path, *, limit: int = 10) -> list[str]:
    """Return up to *limit* files under *directory*, excluding SKILL.md."""
    result: list[str] = []
    if not directory.is_dir():
        return result

    for root, _dirs, files in os.walk(directory):
        for fname in sorted(files):
            if fname == "SKILL.md":
                continue
            result.append(str(Path(root) / fname))
            if len(result) >= limit:
                return result
    return result
