"""Tests for app.plugin.manager — plugin enable/disable lifecycle."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.plugin.loader import PluginLoadResult
from app.plugin.manager import PluginManager
from app.plugin.parser import PluginMeta
from app.schemas.agent import AgentInfo
from app.skill.model import SkillInfo
from app.skill.registry import SkillRegistry


def _make_skill(name: str) -> SkillInfo:
    return SkillInfo(name=name, description="test", location="/tmp", content="body")


def _make_meta(name: str) -> PluginMeta:
    return PluginMeta(
        name=name, version="1.0", description="test", author="test", directory=Path("/tmp")
    )


def _make_load_result(plugin_name: str) -> tuple[PluginLoadResult, dict[str, PluginMeta]]:
    skill = _make_skill(f"{plugin_name}:greet")
    agent = AgentInfo(name=plugin_name, description="test", mode="subagent")
    result = PluginLoadResult(skills=[skill], agents=[agent])
    meta_map = {plugin_name: _make_meta(plugin_name)}
    return result, meta_map


class TestPluginManager:
    def test_register_creates_plugin_info(self, tmp_path: Path):
        sr = SkillRegistry()
        sr.register(_make_skill("myplugin:greet"))
        pm = PluginManager(sr, project_dir=str(tmp_path))
        result, meta_map = _make_load_result("myplugin")
        pm.register_loaded(result, "project", meta_map)
        status = pm.status()
        assert "myplugin" in status

    def test_disabled_by_default_unregisters_skills(self, tmp_path: Path):
        sr = SkillRegistry()
        sr.register(_make_skill("myplugin:greet"))
        pm = PluginManager(sr, project_dir=str(tmp_path))
        result, meta_map = _make_load_result("myplugin")
        pm.register_loaded(result, "project", meta_map)
        # Skill should be unregistered since plugin is disabled by default
        assert sr.get("myplugin:greet") is None

    def test_enable_registers_skills(self, tmp_path: Path):
        sr = SkillRegistry()
        sr.register(_make_skill("myplugin:greet"))
        pm = PluginManager(sr, project_dir=str(tmp_path))
        result, meta_map = _make_load_result("myplugin")
        pm.register_loaded(result, "project", meta_map)
        assert pm.enable("myplugin") is True
        assert sr.get("myplugin:greet") is not None

    def test_disable_unregisters_skills(self, tmp_path: Path):
        sr = SkillRegistry()
        sr.register(_make_skill("myplugin:greet"))
        pm = PluginManager(sr, project_dir=str(tmp_path))
        result, meta_map = _make_load_result("myplugin")
        pm.register_loaded(result, "project", meta_map)
        pm.enable("myplugin")
        assert pm.disable("myplugin") is True
        assert sr.get("myplugin:greet") is None

    def test_enable_already_enabled_returns_false(self, tmp_path: Path):
        sr = SkillRegistry()
        sr.register(_make_skill("myplugin:greet"))
        pm = PluginManager(sr, project_dir=str(tmp_path))
        result, meta_map = _make_load_result("myplugin")
        pm.register_loaded(result, "project", meta_map)
        pm.enable("myplugin")
        assert pm.enable("myplugin") is False

    def test_enable_unknown_returns_false(self, tmp_path: Path):
        sr = SkillRegistry()
        pm = PluginManager(sr, project_dir=str(tmp_path))
        assert pm.enable("unknown") is False

    def test_status_returns_all(self, tmp_path: Path):
        sr = SkillRegistry()
        sr.register(_make_skill("a:greet"))
        sr.register(_make_skill("b:greet"))
        pm = PluginManager(sr, project_dir=str(tmp_path))
        r1, m1 = _make_load_result("a")
        r2, m2 = _make_load_result("b")
        pm.register_loaded(r1, "project", m1)
        pm.register_loaded(r2, "project", m2)
        assert len(pm.status()) == 2

    def test_detail_unknown_returns_none(self, tmp_path: Path):
        sr = SkillRegistry()
        pm = PluginManager(sr, project_dir=str(tmp_path))
        assert pm.detail("nonexistent") is None

    def test_persistence_round_trip(self, tmp_path: Path):
        sr = SkillRegistry()
        sr.register(_make_skill("myplugin:greet"))
        pm = PluginManager(sr, project_dir=str(tmp_path))
        result, meta_map = _make_load_result("myplugin")
        pm.register_loaded(result, "project", meta_map)
        pm.enable("myplugin")

        # New manager instance reads persisted state
        sr2 = SkillRegistry()
        sr2.register(_make_skill("myplugin:greet"))
        pm2 = PluginManager(sr2, project_dir=str(tmp_path))
        result2, meta_map2 = _make_load_result("myplugin")
        pm2.register_loaded(result2, "project", meta_map2)
        # Plugin should be enabled because it was persisted
        detail = pm2.detail("myplugin")
        assert detail is not None
        assert detail["enabled"] is True
