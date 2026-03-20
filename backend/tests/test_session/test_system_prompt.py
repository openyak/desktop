"""System prompt builder tests."""

from pathlib import Path

import pytest

from app.agent.agent import AgentRegistry
from app.session.system_prompt import build_system_prompt


class TestSystemPrompt:
    def test_build_agent_has_prompt(self):
        ar = AgentRegistry()
        build = ar.get("build")
        prompt = build_system_prompt(build)
        assert "software engineering" in prompt.lower() or "tool" in prompt.lower()

    def test_includes_environment(self):
        ar = AgentRegistry()
        build = ar.get("build")
        prompt = build_system_prompt(build)
        assert "Working directory" in prompt
        assert "Platform" in prompt
        assert "date" in prompt

    def test_plan_agent_prompt(self):
        ar = AgentRegistry()
        plan = ar.get("plan")
        prompt = build_system_prompt(plan)
        assert "PLAN MODE" in prompt or "read-only" in prompt.lower()

    def test_with_project_instructions(self, tmp_path: Path):
        instructions = tmp_path / "AGENTS.md"
        instructions.write_text("# Custom Instructions\nDo X and Y.")

        ar = AgentRegistry()
        build = ar.get("build")
        prompt = build_system_prompt(build, directory=str(tmp_path))
        assert "Custom Instructions" in prompt
        assert "Do X and Y" in prompt

    def test_without_project_instructions(self, tmp_path: Path):
        ar = AgentRegistry()
        build = ar.get("build")
        prompt = build_system_prompt(build, directory=str(tmp_path))
        assert "Project Instructions" not in prompt
