"""Verify office skill files parse correctly."""

from pathlib import Path

import pytest

from app.skill.model import parse_skill_file

SKILLS_DIR = Path(__file__).parent.parent.parent / "app" / "data" / "skills"


@pytest.mark.parametrize(
    "skill_name",
    ["pdf", "docx", "xlsx", "pptx", "doc-coauthoring"],
)
def test_office_skill_parses(skill_name: str):
    skill_file = SKILLS_DIR / skill_name / "SKILL.md"
    assert skill_file.exists(), f"Skill file not found: {skill_file}"

    skill = parse_skill_file(skill_file)
    assert skill is not None, f"Failed to parse skill: {skill_name}"
    assert skill.name == skill_name
    assert len(skill.description) > 10
    assert len(skill.content) > 50


@pytest.mark.parametrize(
    "skill_name",
    ["pdf", "docx", "xlsx", "pptx", "doc-coauthoring"],
)
def test_office_skill_has_description(skill_name: str):
    skill_file = SKILLS_DIR / skill_name / "SKILL.md"
    skill = parse_skill_file(skill_file)
    assert skill is not None
    # Description should be meaningful, not just a few words
    assert len(skill.description.split()) >= 3


@pytest.mark.parametrize(
    "skill_name,expected_files",
    [
        ("pdf", ["reference.md", "forms.md"]),
        ("docx", ["reference.md"]),
        ("xlsx", ["reference.md"]),
        ("pptx", ["reference.md"]),
    ],
)
def test_office_skill_bundled_files(skill_name: str, expected_files: list[str]):
    """Verify that expected bundled files exist alongside SKILL.md."""
    skill_dir = SKILLS_DIR / skill_name
    for fname in expected_files:
        fpath = skill_dir / fname
        assert fpath.exists(), f"Missing bundled file: {fpath}"
        assert fpath.stat().st_size > 0, f"Empty bundled file: {fpath}"
