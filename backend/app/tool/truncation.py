"""Tool output truncation — mirrors OpenCode's tool/truncation.ts.

Large outputs are saved to disk so the agent can access them via Read/Grep
without blowing up the context window.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from app.utils.id import generate_ulid

logger = logging.getLogger(__name__)

MAX_LINES = 2000
MAX_BYTES = 50 * 1024  # 50 KB
OUTPUT_DIR_NAME = "tool-output"
RETENTION_SECONDS = 7 * 24 * 3600  # 7 days


@dataclass
class TruncationResult:
    """Result of truncation check."""

    content: str
    truncated: bool
    output_path: str | None = None  # set when truncated=True


def _get_output_dir(workspace: str | None) -> Path:
    """Return output directory, creating if needed."""
    base = Path(workspace) if workspace else Path(".")
    d = base / ".openyak" / OUTPUT_DIR_NAME
    d.mkdir(parents=True, exist_ok=True)
    return d


def truncate_output(
    text: str,
    *,
    workspace: str | None = None,
    max_lines: int = MAX_LINES,
    max_bytes: int = MAX_BYTES,
    direction: Literal["head", "tail"] = "head",
    has_task_tool: bool = False,
) -> TruncationResult:
    """Truncate tool output; save full text to file if oversized.

    Mirrors OpenCode ``Truncate.output()``.

    When output exceeds *max_lines* or *max_bytes* the full text is written to
    a file under ``{workspace}/.openyak/tool-output/`` and a truncated preview
    with a hint is returned so the agent can use Read/Grep to access the rest.
    """
    lines = text.split("\n")
    total_bytes = len(text.encode("utf-8"))

    if len(lines) <= max_lines and total_bytes <= max_bytes:
        return TruncationResult(content=text, truncated=False)

    # Build truncated preview
    out: list[str] = []
    byte_count = 0
    hit_bytes = False

    if direction == "head":
        for i, line in enumerate(lines):
            if i >= max_lines:
                break
            size = len(line.encode("utf-8")) + (1 if i > 0 else 0)
            if byte_count + size > max_bytes:
                hit_bytes = True
                break
            out.append(line)
            byte_count += size
    else:  # tail
        for i in range(len(lines) - 1, -1, -1):
            if len(out) >= max_lines:
                break
            size = len(lines[i].encode("utf-8")) + (1 if out else 0)
            if byte_count + size > max_bytes:
                hit_bytes = True
                break
            out.insert(0, lines[i])
            byte_count += size

    removed = total_bytes - byte_count if hit_bytes else len(lines) - len(out)
    unit = "bytes" if hit_bytes else "lines"
    preview = "\n".join(out)

    # Write full output to file
    output_dir = _get_output_dir(workspace)
    file_id = generate_ulid()
    filepath = output_dir / f"{file_id}.txt"
    filepath.write_text(text, encoding="utf-8")

    # Build hint message
    if has_task_tool:
        hint = (
            f"The tool call succeeded but the output was truncated. "
            f"Full output saved to: {filepath}\n"
            f"Use the Task tool to have explore agent process this file "
            f"with Grep and Read (with offset/limit). "
            f"Do NOT read the full file yourself — delegate to save context."
        )
    else:
        hint = (
            f"The tool call succeeded but the output was truncated. "
            f"Full output saved to: {filepath}\n"
            f"Use Grep to search the full content or "
            f"Read with offset/limit to view specific sections."
        )

    if direction == "head":
        message = f"{preview}\n\n...{removed} {unit} truncated...\n\n{hint}"
    else:
        message = f"...{removed} {unit} truncated...\n\n{hint}\n\n{preview}"

    return TruncationResult(
        content=message, truncated=True, output_path=str(filepath)
    )


def cleanup_old_outputs(workspace: str | None = None) -> int:
    """Remove output files older than RETENTION_SECONDS. Returns count removed."""
    # Don't use _get_output_dir() here — it creates the directory.
    # Cleanup should be a no-op if no truncation has ever happened.
    base = Path(workspace) if workspace else Path(".")
    output_dir = base / ".openyak" / OUTPUT_DIR_NAME
    if not output_dir.exists():
        return 0
    removed = 0
    cutoff = time.time() - RETENTION_SECONDS
    for f in output_dir.iterdir():
        if f.is_file() and f.stat().st_mtime < cutoff:
            f.unlink(missing_ok=True)
            removed += 1
    if removed:
        logger.info("Cleaned up %d old tool output files", removed)
    return removed
