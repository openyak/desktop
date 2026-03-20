"""Tool listing endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request

router = APIRouter()


@router.get("/tools")
async def list_tools(request: Request) -> list[dict[str, Any]]:
    """List all registered tools with their descriptions."""
    registry = request.app.state.tool_registry
    return [
        {"id": tool.id, "description": tool.description}
        for tool in registry.all_tools()
        if tool.id != "invalid"  # Hide internal fallback
    ]


@router.get("/tools/{tool_id}")
async def get_tool(request: Request, tool_id: str) -> dict[str, Any]:
    """Get tool details including JSON Schema."""
    registry = request.app.state.tool_registry
    tool = registry.get(tool_id)
    if tool is None:
        raise HTTPException(status_code=404, detail=f"Tool not found: {tool_id}")
    return {
        "id": tool.id,
        "description": tool.description,
        "parameters": tool.parameters_schema(),
    }
