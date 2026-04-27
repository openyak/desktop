"""Present file tool — explicitly open an existing file for the user."""

from __future__ import annotations

import os
from typing import Any

from app.tool.base import ToolDefinition, ToolResult
from app.tool.context import ToolContext
from app.tool.workspace import WorkspaceViolation, resolve_and_validate


class PresentFileTool(ToolDefinition):

    @property
    def id(self) -> str:
        return "present_file"

    @property
    def is_concurrency_safe(self) -> bool:
        return True

    @property
    def description(self) -> str:
        return (
            "Open an existing file in the user's visual preview panel. "
            "Use this after creating a final deliverable file the user asked for, "
            "or when an existing meaningful file should be shown for inspection. "
            "Do not use it for temporary scripts, scratch files, logs, or helper files."
        )

    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Absolute or workspace-relative path to the file to present",
                },
                "title": {
                    "type": "string",
                    "description": "Optional display title for the preview panel",
                },
            },
            "required": ["file_path"],
        }

    async def execute(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        file_path = args["file_path"]
        try:
            resolved = resolve_and_validate(file_path, ctx.workspace)
        except WorkspaceViolation as e:
            return ToolResult(error=str(e))

        if not os.path.exists(resolved):
            return ToolResult(error=f"File not found: {file_path}")
        if os.path.isdir(resolved):
            return ToolResult(error=f"Cannot present a directory: {file_path}")

        title = args.get("title") or os.path.basename(resolved) or "File Preview"
        return ToolResult(
            output=f"Presented {resolved}",
            title=f"Presented {title}",
            metadata={"file_path": resolved, "title": title},
        )
