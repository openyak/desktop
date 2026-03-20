"""Tests for skill model and frontmatter parser."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.skill.model import SkillInfo, parse_skill_file, _split_frontmatter


# ---------------------------------------------------------------------------
# _split_frontmatter
# ---------------------------------------------------------------------------


class TestSplitFrontmatter:
    def test_valid_frontmatter(self):
        text = "---\nname: test\ndescription: hello\n---\nBody content here"
        fm, body = _split_frontmatter(text)
        assert fm == "name: test\ndescription: hello"
        assert body == "Body content here"

    def test_no_frontmatter(self):
        text = "Just regular markdown\nwith multiple lines"
        fm, body = _split_frontmatter(text)
        assert fm is None
        assert body == text

    def test_unclosed_frontmatter(self):
        text = "---\nname: test\nNo closing delimiter"
        fm, body = _split_frontmatter(text)
        assert fm is None
        assert body == text

    def test_empty_frontmatter(self):
        text = "---\n---\nBody only"
        fm, body = _split_frontmatter(text)
        assert fm == ""
        assert body == "Body only"

    def test_frontmatter_with_blank_body(self):
        text = "---\nname: test\n---\n"
        fm, body = _split_frontmatter(text)
        assert fm == "name: test"
        assert body == ""


# ---------------------------------------------------------------------------
# parse_skill_file
# ---------------------------------------------------------------------------


class TestParseSkillFile:
    def test_valid_skill(self, tmp_path: Path):
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text(
            "---\nname: test-skill\ndescription: A test skill.\n---\n\n# Content\nHello world",
            encoding="utf-8",
        )
        skill = parse_skill_file(skill_file)
        assert skill is not None
        assert skill.name == "test-skill"
        assert skill.description == "A test skill."
        assert "# Content" in skill.content
        assert "Hello world" in skill.content
        assert skill.location == str(skill_file.resolve())

    def test_missing_name(self, tmp_path: Path):
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text(
            "---\ndescription: No name field.\n---\nContent",
            encoding="utf-8",
        )
        assert parse_skill_file(skill_file) is None

    def test_missing_description(self, tmp_path: Path):
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text(
            "---\nname: no-desc\n---\nContent",
            encoding="utf-8",
        )
        assert parse_skill_file(skill_file) is None

    def test_no_frontmatter(self, tmp_path: Path):
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text("# Just markdown\nNo frontmatter.", encoding="utf-8")
        assert parse_skill_file(skill_file) is None

    def test_invalid_yaml(self, tmp_path: Path):
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text(
            "---\n: invalid: yaml: {{{\n---\nContent",
            encoding="utf-8",
        )
        assert parse_skill_file(skill_file) is None

    def test_nonexistent_file(self, tmp_path: Path):
        assert parse_skill_file(tmp_path / "does_not_exist.md") is None

    def test_frontmatter_not_a_dict(self, tmp_path: Path):
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text(
            "---\n- just\n- a\n- list\n---\nContent",
            encoding="utf-8",
        )
        assert parse_skill_file(skill_file) is None

    def test_name_not_string(self, tmp_path: Path):
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text(
            "---\nname: 123\ndescription: Number name.\n---\nContent",
            encoding="utf-8",
        )
        # 123 is an int, not a string
        assert parse_skill_file(skill_file) is None
