"""Lightweight patch format parser.

Supports a custom patch language designed for LLM-generated edits:

    *** Begin Patch
    *** Add File: path/to/new.txt
    +line1
    +line2
    *** Update File: path/to/existing.py
    *** Move to: path/to/renamed.py
    @@ def some_function():
    -old line
    +new line
    *** Delete File: path/to/obsolete.txt
    *** End Patch

This format is more concise and LLM-friendly than unified diff.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class HunkType(str, Enum):
    ADD = "add"
    UPDATE = "update"
    DELETE = "delete"


@dataclass
class Chunk:
    """A single change within an update hunk."""

    context: list[str] = field(default_factory=list)
    removals: list[str] = field(default_factory=list)
    additions: list[str] = field(default_factory=list)


@dataclass
class Hunk:
    """A file-level operation."""

    type: HunkType
    path: str
    move_to: str | None = None  # Only for UPDATE with rename
    contents: str = ""  # Only for ADD
    chunks: list[Chunk] = field(default_factory=list)  # Only for UPDATE


@dataclass
class ParseResult:
    hunks: list[Hunk] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def parse_patch(text: str) -> ParseResult:
    """Parse patch text into a list of hunks."""
    lines = text.split("\n")
    result = ParseResult()
    i = 0

    # Find *** Begin Patch
    while i < len(lines):
        if lines[i].strip() == "*** Begin Patch":
            i += 1
            break
        i += 1
    else:
        result.errors.append("Missing '*** Begin Patch' marker")
        return result

    current_hunk: Hunk | None = None
    current_chunk: Chunk | None = None

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if stripped == "*** End Patch":
            # Finalise current hunk
            if current_hunk is not None:
                if current_chunk is not None and current_hunk.type == HunkType.UPDATE:
                    current_hunk.chunks.append(current_chunk)
                result.hunks.append(current_hunk)
            break

        # --- File operation headers ---
        if stripped.startswith("*** Add File: "):
            # Finalise previous hunk
            if current_hunk is not None:
                if current_chunk is not None and current_hunk.type == HunkType.UPDATE:
                    current_hunk.chunks.append(current_chunk)
                result.hunks.append(current_hunk)
                current_chunk = None

            path = stripped[len("*** Add File: "):]
            current_hunk = Hunk(type=HunkType.ADD, path=path)
            i += 1
            # Collect added lines (prefixed with +)
            add_lines: list[str] = []
            while i < len(lines):
                l = lines[i]
                if l.startswith("+"):
                    add_lines.append(l[1:])
                    i += 1
                elif l.strip().startswith("***"):
                    break
                else:
                    # Blank or context line in add block — treat as content
                    add_lines.append(l[1:] if l.startswith(" ") else l)
                    i += 1
            current_hunk.contents = "\n".join(add_lines)
            if add_lines:
                current_hunk.contents += "\n"
            continue

        if stripped.startswith("*** Delete File: "):
            if current_hunk is not None:
                if current_chunk is not None and current_hunk.type == HunkType.UPDATE:
                    current_hunk.chunks.append(current_chunk)
                result.hunks.append(current_hunk)
                current_chunk = None
            path = stripped[len("*** Delete File: "):]
            current_hunk = Hunk(type=HunkType.DELETE, path=path)
            i += 1
            continue

        if stripped.startswith("*** Update File: "):
            if current_hunk is not None:
                if current_chunk is not None and current_hunk.type == HunkType.UPDATE:
                    current_hunk.chunks.append(current_chunk)
                result.hunks.append(current_hunk)
                current_chunk = None
            path = stripped[len("*** Update File: "):]
            current_hunk = Hunk(type=HunkType.UPDATE, path=path)
            i += 1
            continue

        if stripped.startswith("*** Move to: "):
            if current_hunk is not None and current_hunk.type == HunkType.UPDATE:
                current_hunk.move_to = stripped[len("*** Move to: "):]
            i += 1
            continue

        if stripped == "*** End of File":
            i += 1
            continue

        # --- Chunk content (within UPDATE hunks) ---
        if current_hunk is not None and current_hunk.type == HunkType.UPDATE:
            if stripped.startswith("@@"):
                # New chunk — context line
                if current_chunk is not None:
                    current_hunk.chunks.append(current_chunk)
                current_chunk = Chunk()
                # The @@ line itself is a context hint (function name etc.)
                ctx_text = stripped[2:].strip()
                if ctx_text:
                    current_chunk.context.append(ctx_text)
                i += 1
                continue

            if current_chunk is None:
                current_chunk = Chunk()

            if line.startswith("-"):
                current_chunk.removals.append(line[1:])
            elif line.startswith("+"):
                current_chunk.additions.append(line[1:])
            elif line.startswith(" "):
                current_chunk.context.append(line[1:])
            # else: ignore unrecognised lines

        i += 1

    else:
        # Reached end of lines without *** End Patch
        if current_hunk is not None:
            if current_chunk is not None and current_hunk.type == HunkType.UPDATE:
                current_hunk.chunks.append(current_chunk)
            result.hunks.append(current_hunk)
        result.errors.append("Missing '*** End Patch' marker")

    return result


def apply_chunks(original: str, chunks: list[Chunk]) -> str:
    """Apply a list of chunks to an original file's contents.

    For each chunk:
    1. Locate the context lines in the file to find the edit position.
    2. Remove the lines marked for deletion.
    3. Insert the lines marked for addition.

    Returns the modified file contents.
    """
    lines = original.split("\n")
    # Track if original ended with newline
    trailing_newline = original.endswith("\n")
    # Remove trailing empty string from split if original ended with \n
    if trailing_newline and lines and lines[-1] == "":
        lines = lines[:-1]

    for chunk in chunks:
        if not chunk.context and not chunk.removals:
            # Pure insertion at end of file
            lines.extend(chunk.additions)
            continue

        # Find the position using context lines
        pos = _find_context_position(lines, chunk)
        if pos is None:
            # Fallback: try to find by removal lines
            pos = _find_removal_position(lines, chunk)
        if pos is None:
            # Last resort: append additions
            lines.extend(chunk.additions)
            continue

        # Apply: remove old lines, insert new lines
        remove_count = len(chunk.removals)
        if remove_count > 0:
            # Verify removals match
            for j, removal in enumerate(chunk.removals):
                idx = pos + j
                if idx < len(lines) and lines[idx].rstrip() == removal.rstrip():
                    continue
                # Mismatch — try to proceed anyway
            del lines[pos : pos + remove_count]

        # Insert additions at the same position
        for j, addition in enumerate(chunk.additions):
            lines.insert(pos + j, addition)

    result = "\n".join(lines)
    if trailing_newline:
        result += "\n"
    return result


def _find_context_position(lines: list[str], chunk: Chunk) -> int | None:
    """Find where in *lines* the chunk's context matches, returning the index
    where removals/additions should be applied (right after context)."""
    if not chunk.context:
        return None

    # Search for the first context line
    target = chunk.context[0].rstrip()
    for i, line in enumerate(lines):
        if line.rstrip() == target:
            # Check if all context lines match consecutively
            all_match = True
            for j, ctx in enumerate(chunk.context):
                idx = i + j
                if idx >= len(lines) or lines[idx].rstrip() != ctx.rstrip():
                    all_match = False
                    break
            if all_match:
                # Position right after context
                return i + len(chunk.context)
    return None


def _find_removal_position(lines: list[str], chunk: Chunk) -> int | None:
    """Find where the removal lines appear in the file."""
    if not chunk.removals:
        return None

    target = chunk.removals[0].rstrip()
    for i, line in enumerate(lines):
        if line.rstrip() == target:
            all_match = True
            for j, rem in enumerate(chunk.removals):
                idx = i + j
                if idx >= len(lines) or lines[idx].rstrip() != rem.rstrip():
                    all_match = False
                    break
            if all_match:
                return i
    return None
