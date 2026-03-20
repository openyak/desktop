"""Skill listing endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request

router = APIRouter()


def _skill_source(skill_name: str, location: str, request: Request) -> str:
    """Determine the source of a skill: 'plugin', 'bundled', or 'project'."""
    if ":" in skill_name:
        return "plugin"
    # Check if location is under the bundled data directory
    if "/data/skills/" in location or "\\data\\skills\\" in location:
        return "bundled"
    return "project"


@router.get("/skills")
async def list_skills(request: Request) -> list[dict[str, Any]]:
    """List all discovered skills."""
    registry = request.app.state.skill_registry
    return [
        {
            "name": skill.name,
            "description": skill.description,
            "location": skill.location,
            "source": _skill_source(skill.name, skill.location, request),
        }
        for skill in registry.all_skills()
    ]


@router.get("/skills/{skill_name}")
async def get_skill(request: Request, skill_name: str) -> dict[str, Any]:
    """Get skill details including full content."""
    registry = request.app.state.skill_registry
    skill = registry.get(skill_name)
    if skill is None:
        raise HTTPException(status_code=404, detail=f"Skill not found: {skill_name}")
    return {
        "name": skill.name,
        "description": skill.description,
        "location": skill.location,
        "content": skill.content,
    }
