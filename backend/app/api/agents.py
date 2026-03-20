"""Agent listing endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from app.schemas.agent import AgentInfo

router = APIRouter()


@router.get("/agents", response_model=list[AgentInfo])
async def list_agents(request: Request, include_hidden: bool = False) -> list[AgentInfo]:
    """List all registered agents."""
    registry = request.app.state.agent_registry
    return registry.list_agents(include_hidden=include_hidden)


@router.get("/agents/{name}", response_model=AgentInfo)
async def get_agent(request: Request, name: str) -> AgentInfo:
    """Get agent details by name."""
    registry = request.app.state.agent_registry
    agent = registry.get(name)
    if agent is None:
        raise HTTPException(status_code=404, detail=f"Agent not found: {name}")
    return agent
