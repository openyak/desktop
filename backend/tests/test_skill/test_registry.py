"""Tests for skill registry."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.skill.registry import SkillRegistry


def _create_skill(base_dir: Path, name: str, desc: str) -> Path:
    """Helper: create a SKILL.md file under base_dir/<name>/."""
    skill_dir = base_dir / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text(
        f"---\nname: {name}\ndescription: {desc}\n---\n\n# {name}\nContent.",
        encoding="utf-8",
    )
    return skill_file


class TestSkillRegistry:
    def test_scan_project_skills(self, tmp_path: Path):
        skills_dir = tmp_path / ".openyak" / "skills"
        _create_skill(skills_dir, "my-skill", "A project skill.")

        registry = SkillRegistry()
        registry.scan(project_dir=str(tmp_path))

        assert registry.count == 1
        skill = registry.get("my-skill")
        assert skill is not None
        assert skill.description == "A project skill."

    def test_scan_external_claude_skills(self, tmp_path: Path):
        skills_dir = tmp_path / ".claude" / "skills"
        _create_skill(skills_dir, "claude-skill", "From .claude")

        registry = SkillRegistry()
        registry.scan(project_dir=str(tmp_path))

        assert registry.get("claude-skill") is not None

    def test_scan_external_agents_skills(self, tmp_path: Path):
        skills_dir = tmp_path / ".agents" / "skills"
        _create_skill(skills_dir, "agents-skill", "From .agents")

        registry = SkillRegistry()
        registry.scan(project_dir=str(tmp_path))

        assert registry.get("agents-skill") is not None

    def test_scan_bundled_skills(self, tmp_path: Path):
        bundled = tmp_path / "bundled"
        _create_skill(bundled, "bundled-skill", "Bundled with app.")

        registry = SkillRegistry(bundled_dir=bundled)
        registry.scan()

        assert registry.get("bundled-skill") is not None

    def test_project_overrides_bundled(self, tmp_path: Path):
        bundled = tmp_path / "bundled"
        _create_skill(bundled, "shared", "From bundled")

        project = tmp_path / "project"
        project_skills = project / ".openyak" / "skills"
        _create_skill(project_skills, "shared", "From project")

        registry = SkillRegistry(bundled_dir=bundled)
        registry.scan(project_dir=str(project))

        skill = registry.get("shared")
        assert skill is not None
        assert skill.description == "From project"

    def test_empty_registry(self):
        registry = SkillRegistry()
        registry.scan()
        assert registry.count == 0
        assert registry.all_skills() == []
        assert registry.get("nothing") is None

    def test_skill_names(self, tmp_path: Path):
        bundled = tmp_path / "bundled"
        _create_skill(bundled, "alpha", "First")
        _create_skill(bundled, "beta", "Second")

        registry = SkillRegistry(bundled_dir=bundled)
        registry.scan()

        names = registry.skill_names()
        assert "alpha" in names
        assert "beta" in names
        assert len(names) == 2

    def test_all_skills_returns_list(self, tmp_path: Path):
        bundled = tmp_path / "bundled"
        _create_skill(bundled, "one", "Skill one")

        registry = SkillRegistry(bundled_dir=bundled)
        registry.scan()

        skills = registry.all_skills()
        assert len(skills) == 1
        assert skills[0].name == "one"

    def test_invalid_skill_file_skipped(self, tmp_path: Path):
        skills_dir = tmp_path / ".openyak" / "skills" / "bad"
        skills_dir.mkdir(parents=True)
        (skills_dir / "SKILL.md").write_text(
            "No frontmatter at all", encoding="utf-8"
        )

        registry = SkillRegistry()
        registry.scan(project_dir=str(tmp_path))

        assert registry.count == 0
