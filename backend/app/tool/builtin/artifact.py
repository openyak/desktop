"""Artifact tool — create, update, and rewrite artifacts in the viewer panel.

Supports three commands modeled after Claude.ai:
  - create:  New artifact with full content
  - update:  Targeted old_str→new_str replacement (token-efficient)
  - rewrite: Full content replacement for major changes
"""

from __future__ import annotations

import logging
from typing import Any

from app.tool.base import ToolDefinition, ToolResult
from app.tool.context import ToolContext

log = logging.getLogger(__name__)


class ArtifactTool(ToolDefinition):

    @property
    def id(self) -> str:
        return "artifact"

    @property
    def description(self) -> str:
        return (
            "Manage artifacts in the visual preview panel. Commands:\n"
            "- 'create': Generate a new artifact with full content\n"
            "- 'update': Targeted string replacement using old_str/new_str (token-efficient)\n"
            "- 'rewrite': Full content replacement for major changes\n"
            "Use this for interactive or visual content: React components, HTML pages, "
            "SVG graphics, code files, Markdown documents, or Mermaid diagrams."
        )

    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "enum": ["create", "update", "rewrite"],
                    "description": (
                        "The operation: 'create' for a new artifact, "
                        "'update' for targeted old_str→new_str replacement, "
                        "'rewrite' for full content replacement."
                    ),
                },
                "identifier": {
                    "type": "string",
                    "description": (
                        "A stable kebab-case identifier for the artifact. "
                        "Reuse the same identifier across create/update/rewrite "
                        "to track the artifact across iterations."
                    ),
                },
                "type": {
                    "type": "string",
                    "enum": ["react", "html", "svg", "code", "markdown", "mermaid"],
                    "description": "The artifact type (required for 'create').",
                },
                "title": {
                    "type": "string",
                    "description": "A brief, descriptive title (required for 'create').",
                },
                "content": {
                    "type": "string",
                    "description": "Full content for 'create' or 'rewrite' commands.",
                },
                "old_str": {
                    "type": "string",
                    "description": "The exact string to find (for 'update' command).",
                },
                "new_str": {
                    "type": "string",
                    "description": "The replacement string (for 'update' command).",
                },
                "language": {
                    "type": "string",
                    "description": "Programming language for 'code' type (e.g. 'python').",
                },
            },
            "required": ["command", "identifier"],
        }

    def _get_cache(self, ctx: ToolContext) -> dict[str, dict[str, Any]]:
        """Get the artifact cache from the GenerationJob."""
        job = getattr(ctx, "_job", None)
        if job is not None:
            return getattr(job, "artifact_cache", {})
        return {}

    async def execute(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        command = args.get("command", "create")
        identifier = args.get("identifier", "")
        artifact_type = args.get("type")
        title = args.get("title")
        language = args.get("language")
        cache = self._get_cache(ctx)

        if command == "create":
            content = args.get("content", "")
            if not artifact_type or not title or not content:
                return ToolResult(
                    error="'create' requires 'type', 'title', and 'content' parameters.",
                )

            cache[identifier] = {
                "content": content,
                "type": artifact_type,
                "title": title,
                "language": language,
            }

            return ToolResult(
                output=f"Artifact '{title}' created.",
                metadata={
                    "command": "create",
                    "type": artifact_type,
                    "title": title,
                    "identifier": identifier,
                    "language": language,
                    "content": content,
                },
            )

        elif command == "update":
            old_str = args.get("old_str", "")
            new_str = args.get("new_str", "")
            if not old_str:
                return ToolResult(error="'update' requires 'old_str' parameter.")

            cached = cache.get(identifier)
            if not cached:
                return ToolResult(
                    error=(
                        f"No artifact found with identifier '{identifier}'. "
                        "Use 'create' command first."
                    ),
                )

            current_content = cached["content"]
            if old_str not in current_content:
                return ToolResult(
                    error=(
                        f"old_str not found in artifact '{identifier}'. "
                        f"The content may have changed. "
                        f"Current content length: {len(current_content)} chars."
                    ),
                )

            new_content = current_content.replace(old_str, new_str, 1)
            cached["content"] = new_content
            if title:
                cached["title"] = title
            if artifact_type:
                cached["type"] = artifact_type

            return ToolResult(
                output=f"Artifact '{identifier}' updated ({len(old_str)} chars replaced).",
                metadata={
                    "command": "update",
                    "type": cached["type"],
                    "title": title or cached["title"],
                    "identifier": identifier,
                    "language": cached.get("language") or language,
                    "content": new_content,
                },
            )

        elif command == "rewrite":
            content = args.get("content", "")
            if not content:
                return ToolResult(error="'rewrite' requires 'content' parameter.")

            cached = cache.get(identifier)
            if not cached:
                return ToolResult(
                    error=(
                        f"No artifact found with identifier '{identifier}'. "
                        "Use 'create' command first."
                    ),
                )

            cached["content"] = content
            if title:
                cached["title"] = title
            if artifact_type:
                cached["type"] = artifact_type

            return ToolResult(
                output=f"Artifact '{identifier}' rewritten.",
                metadata={
                    "command": "rewrite",
                    "type": artifact_type or cached["type"],
                    "title": title or cached["title"],
                    "identifier": identifier,
                    "language": cached.get("language") or language,
                    "content": content,
                },
            )

        else:
            return ToolResult(error=f"Unknown command: '{command}'")
