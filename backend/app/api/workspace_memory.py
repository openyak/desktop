"""API endpoints for workspace-scoped memory."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.dependencies import get_session_factory

router = APIRouter(prefix="/workspace-memory")


class WorkspaceMemoryResponse(BaseModel):
    workspace_path: str
    content: str
    time_updated: str | None = None


class WorkspaceMemoryListItem(BaseModel):
    workspace_path: str
    content: str
    line_count: int
    time_updated: str | None = None


class WorkspaceMemoryUpdate(BaseModel):
    workspace_path: str = Field(min_length=1)
    content: str


@router.get("/list", response_model=list[WorkspaceMemoryListItem])
async def list_workspace_memories_endpoint(
    session_factory=Depends(get_session_factory),
):
    """List all workspace memories."""
    from app.memory.workspace_memory_storage import list_workspace_memories

    items = await list_workspace_memories(session_factory)
    return [WorkspaceMemoryListItem(**item) for item in items]


@router.get("", response_model=WorkspaceMemoryResponse)
async def get_workspace_memory_endpoint(
    workspace_path: str,
    session_factory=Depends(get_session_factory),
):
    """Get the memory content for a workspace."""
    from app.memory.workspace_memory_storage import get_workspace_memory_with_timestamp

    content, time_updated = await get_workspace_memory_with_timestamp(
        session_factory, workspace_path
    )
    return WorkspaceMemoryResponse(
        workspace_path=workspace_path,
        content=content or "",
        time_updated=time_updated,
    )


@router.put("", response_model=dict)
async def update_workspace_memory_endpoint(
    request: WorkspaceMemoryUpdate,
    session_factory=Depends(get_session_factory),
):
    """Create or update the memory for a workspace."""
    from app.memory.workspace_memory_storage import upsert_workspace_memory

    await upsert_workspace_memory(
        session_factory, request.workspace_path, request.content
    )
    return {"status": "ok"}


@router.delete("", response_model=dict)
async def delete_workspace_memory_endpoint(
    workspace_path: str,
    session_factory=Depends(get_session_factory),
):
    """Delete the memory for a workspace."""
    from app.memory.workspace_memory_storage import delete_workspace_memory

    removed = await delete_workspace_memory(session_factory, workspace_path)
    return {"removed": removed}


@router.post("/export", response_model=dict)
async def export_workspace_memory_endpoint(
    workspace_path: str,
    session_factory=Depends(get_session_factory),
):
    """Export workspace memory to a .openyak/memory.md file in the workspace."""
    from app.memory.workspace_memory_storage import get_workspace_memory

    content = await get_workspace_memory(session_factory, workspace_path)
    if content is None:
        raise HTTPException(status_code=404, detail="No memory found for this workspace")

    target_dir = Path(workspace_path) / ".openyak"
    target_file = target_dir / "memory.md"

    try:
        os.makedirs(target_dir, exist_ok=True)
        target_file.write_text(content, encoding="utf-8")
    except OSError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to export memory: {e}",
        )

    return {"exported_to": str(target_file)}
