"""System prompt builder tests."""

from pathlib import Path

import pytest

from app.dependencies import set_skill_registry
from app.skill.registry import SkillRegistry
from app.agent.agent import AgentRegistry
from app.session.system_prompt import build_system_prompt


class TestSystemPrompt:
    def test_build_agent_has_prompt(self):
        ar = AgentRegistry()
        build = ar.get("build")
        parts = build_system_prompt(build)
        prompt = parts.as_plain_text()
        assert "software engineering" in prompt.lower() or "tool" in prompt.lower()

    def test_includes_environment(self):
        ar = AgentRegistry()
        build = ar.get("build")
        parts = build_system_prompt(build)
        prompt = parts.as_plain_text()
        assert "Working directory" in prompt
        assert "Platform" in prompt
        assert "date" in prompt

    def test_plan_agent_prompt(self):
        ar = AgentRegistry()
        plan = ar.get("plan")
        parts = build_system_prompt(plan)
        prompt = parts.as_plain_text()
        assert "PLAN MODE" in prompt or "read-only" in prompt.lower()

    def test_with_project_instructions(self, tmp_path: Path):
        instructions = tmp_path / "AGENTS.md"
        instructions.write_text("# Custom Instructions\nDo X and Y.")

        ar = AgentRegistry()
        build = ar.get("build")
        parts = build_system_prompt(build, directory=str(tmp_path))
        prompt = parts.as_plain_text()
        assert "Custom Instructions" in prompt
        assert "Do X and Y" in prompt

    def test_without_project_instructions(self, tmp_path: Path):
        ar = AgentRegistry()
        build = ar.get("build")
        parts = build_system_prompt(build, directory=str(tmp_path))
        prompt = parts.as_plain_text()
        assert "Project Instructions" not in prompt

    def test_cached_parts_separate_static_from_dynamic(self):
        ar = AgentRegistry()
        build = ar.get("build")
        parts = build_system_prompt(build)
        # Agent base prompt is in cached section
        assert "Yakyak" in parts.cached or "tool" in parts.cached.lower()
        # Environment info is in dynamic section
        assert "Working directory" in parts.dynamic

    def test_as_cached_blocks_format(self):
        ar = AgentRegistry()
        build = ar.get("build")
        parts = build_system_prompt(build)
        blocks = parts.as_cached_blocks()
        assert len(blocks) == 2
        # First block (cached) has cache_control
        assert blocks[0]["type"] == "text"
        assert blocks[0]["cache_control"] == {"type": "ephemeral"}
        # Second block (dynamic) has no cache_control
        assert blocks[1]["type"] == "text"
        assert "cache_control" not in blocks[1]

    def test_includes_skill_routing_when_skills_available(self, tmp_path: Path):
        skills_dir = tmp_path / ".openyak" / "skills" / "sheet-helper"
        skills_dir.mkdir(parents=True)
        (skills_dir / "SKILL.md").write_text(
            "---\nname: sheet-helper\ndescription: Helps with spreadsheet workflows.\n---\nUse for sheets.",
            encoding="utf-8",
        )

        registry = SkillRegistry(project_dir=str(tmp_path))
        registry.scan(project_dir=str(tmp_path))
        set_skill_registry(registry)

        ar = AgentRegistry()
        build = ar.get("build")
        parts = build_system_prompt(build)

        assert "Skill Routing" in parts.dynamic
        assert "sheet-helper" in parts.dynamic
