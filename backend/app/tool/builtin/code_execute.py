"""Code execution tool — run Python code in a sandboxed subprocess.

Executes Python code in a temporary directory using the backend's own
interpreter (so all installed packages like pandas, numpy, matplotlib
are available). Includes blocked-import checks and output size limits.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from app.tool.base import ToolDefinition, ToolResult
from app.tool.context import ToolContext

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 30  # seconds
MAX_TIMEOUT = 120
MAX_OUTPUT = 51200  # 50 KB

# Use the same Python that runs the backend → same venv, same packages.
_PYTHON = sys.executable

# ---------------------------------------------------------------------------
# Security: blocked imports
# ---------------------------------------------------------------------------
_BLOCKED_IMPORTS = {
    "subprocess",
    "shutil",
    "socket",
    "http.server",
    "xmlrpc",
    "ctypes",
    "multiprocessing",
    "signal",
    "importlib",
    "code",
    "codeop",
    "compileall",
    "py_compile",
}

_IMPORT_PATTERN = re.compile(r"^\s*(?:import|from)\s+([\w.]+)", re.MULTILINE)


def _check_blocked_imports(code: str) -> str | None:
    """Return an error message if *code* contains a blocked import, else None."""
    for imp in _IMPORT_PATTERN.findall(code):
        for blocked in _BLOCKED_IMPORTS:
            if imp == blocked or imp.startswith(blocked + "."):
                return f"Import '{imp}' is not allowed in sandboxed execution"
    return None


# ---------------------------------------------------------------------------
# Tool definition
# ---------------------------------------------------------------------------
class CodeExecuteTool(ToolDefinition):

    @property
    def id(self) -> str:
        return "code_execute"

    @property
    def description(self) -> str:
        return (
            "Execute Python code in a sandboxed subprocess. "
            "The code runs with the backend's Python environment so pandas, "
            "numpy, matplotlib and other installed packages are available. "
            "IMPORTANT: Each call runs in a fresh, isolated process — no state "
            "(variables, imports, data) persists between calls. You MUST include "
            "all imports and data loading in every call. For multi-step analysis, "
            "put ALL code in a single call rather than splitting across multiple calls."
        )

    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Python code to execute",
                },
                "timeout": {
                    "type": "integer",
                    "description": f"Timeout in seconds (default {DEFAULT_TIMEOUT}, max {MAX_TIMEOUT})",
                    "default": DEFAULT_TIMEOUT,
                },
            },
            "required": ["code"],
        }

    async def execute(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        code = args.get("code", "")
        if not code.strip():
            return ToolResult(error="No code provided")

        timeout = min(args.get("timeout", DEFAULT_TIMEOUT), MAX_TIMEOUT)

        # Security check
        import_error = _check_blocked_imports(code)
        if import_error:
            return ToolResult(error=import_error)

        try:
            output, exit_code = await _run_python(code, timeout)
        except subprocess.TimeoutExpired:
            return ToolResult(
                error=f"Execution timed out after {timeout}s",
                metadata={"timeout": True},
            )
        except FileNotFoundError:
            return ToolResult(
                error=f"Python interpreter not found: '{_PYTHON}'"
            )
        except Exception as exc:
            return ToolResult(error=f"Execution failed: {exc}")

        title = f"python: {code[:60]}..." if len(code) > 60 else f"python: {code}"

        return ToolResult(
            output=output,
            title=title,
            metadata={"exit_code": exit_code, "language": "python"},
            error=f"Code execution failed with exit code {exit_code}" if exit_code != 0 else None,
        )


# ---------------------------------------------------------------------------
# Subprocess runner
# ---------------------------------------------------------------------------
async def _run_python(code: str, timeout: int) -> tuple[str, int]:
    """Run *code* in an isolated temp directory and return (output, exit_code)."""

    def _run() -> tuple[str, int]:
        with tempfile.TemporaryDirectory(prefix="openyak_exec_") as tmpdir:
            script = Path(tmpdir) / "script.py"
            script.write_text(code, encoding="utf-8")

            env = os.environ.copy()
            env["PYTHONDONTWRITEBYTECODE"] = "1"

            proc = subprocess.run(
                [_PYTHON, str(script)],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=tmpdir,
                env=env,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
            )

            stdout = (proc.stdout or "")[:MAX_OUTPUT]
            stderr = (proc.stderr or "")[:MAX_OUTPUT]

            parts: list[str] = []
            if stdout:
                parts.append(stdout)
            if stderr:
                parts.append(f"STDERR:\n{stderr}")

            output = "\n".join(parts) if parts else "(no output)"
            if proc.returncode != 0:
                output = f"Exit code: {proc.returncode}\n{output}"

            return output, proc.returncode

    return await asyncio.to_thread(_run)
