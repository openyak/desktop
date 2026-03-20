"""Skill data model and SKILL.md frontmatter parser."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)


@dataclass
class SkillInfo:
    """A discovered skill definition."""

    name: str
    description: str
    location: str  # Absolute path to SKILL.md
    content: str  # Markdown content after frontmatter


def _split_frontmatter(text: str) -> tuple[str | None, str]:
    """Split YAML frontmatter from markdown body.

    Returns (frontmatter_string, body_string).
    If no valid frontmatter delimiters found, returns (None, original_text).
    """
    if not text.startswith("---"):
        return None, text

    # Find the closing ---
    end = text.find("\n---", 3)
    if end == -1:
        return None, text

    frontmatter = text[3:end].strip()
    body = text[end + 4:].strip()  # skip past \n---
    return frontmatter, body


def parse_skill_file(path: Path) -> SkillInfo | None:
    """Parse a SKILL.md file into a SkillInfo.

    Returns None if the file cannot be parsed or lacks required fields.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        logger.debug("Cannot read skill file: %s", path)
        return None

    frontmatter_str, body = _split_frontmatter(text)
    if frontmatter_str is None:
        logger.debug("No frontmatter in %s", path)
        return None

    try:
        data = yaml.safe_load(frontmatter_str)
    except yaml.YAMLError as e:
        logger.warning("Invalid YAML in %s: %s", path, e)
        return None

    if not isinstance(data, dict):
        logger.debug("Frontmatter is not a mapping in %s", path)
        return None

    name = data.get("name")
    description = data.get("description")

    if not name or not isinstance(name, str):
        logger.debug("Missing or invalid 'name' in %s", path)
        return None
    if not description or not isinstance(description, str):
        logger.debug("Missing or invalid 'description' in %s", path)
        return None

    return SkillInfo(
        name=name,
        description=description,
        location=str(path.resolve()),
        content=body,
    )
