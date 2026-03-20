"""Unified diff generation for the edit tool."""

from __future__ import annotations

import difflib


def generate_unified_diff(
    original: str,
    modified: str,
    filename: str = "file",
) -> str:
    """Generate a unified diff between two strings."""
    original_lines = original.splitlines(keepends=True)
    modified_lines = modified.splitlines(keepends=True)
    diff = difflib.unified_diff(
        original_lines,
        modified_lines,
        fromfile=f"a/{filename}",
        tofile=f"b/{filename}",
    )
    return "".join(diff)
