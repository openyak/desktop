"""Bash tool — shell execution with timeout.

Uses subprocess.run in a thread to avoid Windows event-loop issues
(SelectorEventLoop does not support asyncio.create_subprocess_exec).
"""

from __future__ import annotations

import asyncio
import os
import platform
import subprocess
from typing import Any

from app.tool.base import ToolDefinition, ToolResult
from app.tool.context import ToolContext
from app.tool.workspace import WorkspaceViolation, get_default_output_dir, validate_cwd

DEFAULT_TIMEOUT = 120  # 2 minutes
MAX_TIMEOUT = 600  # 10 minutes


class BashTool(ToolDefinition):

    @property
    def id(self) -> str:
        return "bash"

    @property
    def description(self) -> str:
        return (
            "Execute a shell command. Returns stdout and stderr. "
            "Commands run in the project directory. "
            "Timeout defaults to 120 seconds (max 600)."
        )

    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The shell command to execute",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Timeout in seconds (default 120, max 600)",
                    "default": DEFAULT_TIMEOUT,
                },
                "cwd": {
                    "type": "string",
                    "description": "Working directory for the command",
                },
            },
            "required": ["command"],
        }

    async def execute(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        command = args["command"]
        timeout = min(args.get("timeout", DEFAULT_TIMEOUT), MAX_TIMEOUT)
        cwd = args.get("cwd")

        # Workspace restriction: validate/default cwd (defaults to openyak_written/)
        try:
            if not cwd and ctx.workspace:
                cwd = get_default_output_dir(ctx.workspace)
            cwd = validate_cwd(cwd, ctx.workspace)
        except WorkspaceViolation as e:
            return ToolResult(error=str(e))

        # Ensure cwd exists — openyak_written/ may not have been created yet
        if cwd:
            import pathlib
            try:
                pathlib.Path(cwd).mkdir(parents=True, exist_ok=True)
            except OSError:
                # If we can't create it, fall back to workspace or None
                cwd = ctx.workspace or None

        # Use shell=True so the platform picks the right shell automatically
        # (cmd on Windows, /bin/sh on Unix).
        _creation_flags = subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0

        def _run() -> subprocess.CompletedProcess[bytes]:
            return subprocess.run(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=cwd,
                timeout=timeout,
                env={**os.environ},
                creationflags=_creation_flags,
            )

        try:
            result = await asyncio.to_thread(_run)
        except subprocess.TimeoutExpired:
            return ToolResult(
                error=f"Command timed out after {timeout}s",
                metadata={"timeout": True},
            )
        except FileNotFoundError:
            return ToolResult(error="Shell not found")
        except PermissionError:
            return ToolResult(error="Permission denied")

        stdout = result.stdout.decode("utf-8", errors="replace")
        stderr = result.stderr.decode("utf-8", errors="replace")

        output_parts = []
        if stdout:
            output_parts.append(stdout)
        if stderr:
            output_parts.append(f"STDERR:\n{stderr}")

        output = "\n".join(output_parts) if output_parts else "(no output)"
        exit_code = result.returncode

        if exit_code != 0:
            output = f"Exit code: {exit_code}\n{output}"

        return ToolResult(
            output=output,
            title=command[:80],
            metadata={"exit_code": exit_code},
            error=f"Command failed with exit code {exit_code}" if exit_code != 0 else None,
        )
