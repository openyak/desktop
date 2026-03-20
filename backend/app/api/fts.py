"""FTS index management API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

router = APIRouter(prefix="/fts")


class FTSStatus(BaseModel):
    enabled: bool
    active_workspaces: int
    active_sessions: int


class IndexStatus(BaseModel):
    workspace: str
    session_id: str | None = None
    status: str
    file_count: int | None = None
    error: str | None = None


class IndexTriggerResponse(BaseModel):
    workspace: str
    session_id: str | None = None
    message: str


def _get_manager(request: Request):
    """Return the IndexManager from app state, or raise 404 if disabled."""
    manager = getattr(request.app.state, "index_manager", None)
    if manager is None:
        raise HTTPException(status_code=404, detail="FTS is not enabled")
    return manager


@router.get("/status", response_model=FTSStatus)
async def get_fts_status(request: Request) -> FTSStatus:
    """Global FTS status."""
    manager = getattr(request.app.state, "index_manager", None)

    if manager is None:
        return FTSStatus(enabled=False, active_workspaces=0, active_sessions=0)

    return FTSStatus(
        enabled=True,
        active_workspaces=len(manager._dbs),
        active_sessions=len(manager._sessions),
    )


@router.get("/index/{workspace:path}", response_model=IndexStatus)
async def get_index_status(
    request: Request,
    workspace: str,
    session_id: str | None = Query(None),
) -> IndexStatus:
    """Index status for a session's workspace index."""
    manager = _get_manager(request)

    if not session_id:
        return IndexStatus(workspace=workspace, status="not_indexed")

    status = manager.index_status(session_id)
    return IndexStatus(
        workspace=workspace,
        session_id=session_id,
        status=status.get("status", "unknown"),
        file_count=status.get("file_count"),
        error=status.get("error"),
    )


@router.post("/index/{workspace:path}", response_model=IndexTriggerResponse)
async def trigger_index(
    request: Request,
    workspace: str,
    session_id: str | None = Query(None),
) -> IndexTriggerResponse:
    """Initialize and index a workspace for a session."""
    manager = _get_manager(request)

    if not session_id:
        return IndexTriggerResponse(
            workspace=workspace,
            message="session_id required for per-session indexing",
        )

    # Ensure index exists (creates DB + starts auto-index on first access)
    await manager.ensure_index(workspace, session_id)

    # If already indexed, trigger a fresh reindex
    status = manager.index_status(session_id)
    if status.get("status") == "indexed":
        await manager.trigger_reindex(session_id)
        return IndexTriggerResponse(workspace=workspace, session_id=session_id, message="Re-indexing started")

    return IndexTriggerResponse(workspace=workspace, session_id=session_id, message="Indexing started in background")
