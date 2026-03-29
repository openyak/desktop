"""Memory tool — read and update workspace memory that persists across sessions."""

from __future__ import annotations

import logging
from typing import Any

from app.tool.base import ToolDefinition, ToolResult
from app.tool.context import ToolContext

logger = logging.getLogger(__name__)


class MemoryTool(ToolDefinition):
    """Agent-driven workspace memory — read, update, or clear persistent context."""

    @property
    def id(self) -> str:
        return "memory"

    @property
    def description(self) -> str:
        return (
            "Read or update workspace memory that persists across conversations.\n\n"
            "The workspace memory is shown in your system prompt as <workspace-memory>.\n"
            "Use this tool to save important context for future sessions.\n\n"
            "Commands:\n"
            "- read: Show the current workspace memory\n"
            "- update: Add to or replace the workspace memory\n"
        )

    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "enum": ["read", "update"],
                    "description": "The memory operation to perform.",
                },
                "content": {
                    "type": "string",
                    "description": "Content to save (update command only).",
                },
                "mode": {
                    "type": "string",
                    "enum": ["append", "replace"],
                    "description": "How to update: 'append' adds to the end (default), 'replace' overwrites entirely.",
                },
            },
            "required": ["command"],
        }

    async def execute(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        command = args.get("command", "")

        app_state = getattr(ctx, "_app_state", None)
        if not app_state or "session_factory" not in app_state:
            return ToolResult(error="Memory system unavailable (no database connection).")

        session_factory = app_state["session_factory"]
        workspace = ctx.workspace
        if not workspace or workspace == ".":
            return ToolResult(error="No workspace set — memory requires a workspace directory.")

        if command == "read":
            return await self._read(session_factory, workspace)
        elif command == "update":
            return await self._update(args, session_factory, workspace)
        else:
            return ToolResult(error=f"Unknown command: {command}. Use 'read' or 'update'.")

    async def _read(self, session_factory: Any, workspace: str) -> ToolResult:
        from app.memory.workspace_memory_storage import get_workspace_memory

        content = await get_workspace_memory(session_factory, workspace)
        if not content or not content.strip():
            return ToolResult(
                output="(empty — no workspace memory saved yet)",
                title="Memory: empty",
            )
        line_count = len(content.strip().split("\n"))
        return ToolResult(
            output=content,
            title=f"Memory: {line_count} lines",
        )

    async def _update(self, args: dict[str, Any], session_factory: Any, workspace: str) -> ToolResult:
        from app.memory.workspace_memory_storage import (
            get_workspace_memory,
            upsert_workspace_memory,
        )

        content = (args.get("content") or "").strip()
        if not content:
            return ToolResult(error="Content is required for the 'update' command.")

        mode = args.get("mode", "append")

        if mode == "replace":
            new_content = content
        else:
            # Append to existing
            existing = await get_workspace_memory(session_factory, workspace)
            if existing and existing.strip():
                new_content = existing.rstrip("\n") + "\n" + content
            else:
                new_content = content

        await upsert_workspace_memory(session_factory, workspace, new_content)

        line_count = len(new_content.strip().split("\n"))
        action = "Replaced" if mode == "replace" else "Updated"
        logger.info("MemoryTool: %s workspace memory for %s (%d lines)", action.lower(), workspace, line_count)

        return ToolResult(
            output=f"{action} workspace memory ({line_count} lines)",
            title=f"Memory {action.lower()}",
        )
