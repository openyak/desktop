"""Plugin management endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request

router = APIRouter(prefix="/plugins")


def _get_manager(request: Request):
    manager = getattr(request.app.state, "plugin_manager", None)
    if manager is None:
        return None
    return manager


@router.get("/status")
async def plugins_status(request: Request) -> dict[str, Any]:
    """Return status of all installed plugins."""
    manager = _get_manager(request)
    if manager is None:
        return {"plugins": {}}
    return {"plugins": manager.status()}


@router.get("/{name}")
async def plugin_detail(name: str, request: Request) -> dict[str, Any]:
    """Return detailed info for a single plugin."""
    manager = _get_manager(request)
    if manager is None:
        raise HTTPException(status_code=404, detail="Plugin system not available")
    detail = manager.detail(name)
    if detail is None:
        raise HTTPException(status_code=404, detail=f"Plugin not found: {name}")
    return detail


@router.post("/{name}/enable")
async def enable_plugin(name: str, request: Request) -> dict[str, Any]:
    """Enable a disabled plugin."""
    manager = _get_manager(request)
    if manager is None:
        return {"success": False, "error": "Plugin system not available"}
    success = manager.enable(name)
    return {"success": success, "plugins": manager.status()}


@router.post("/{name}/disable")
async def disable_plugin(name: str, request: Request) -> dict[str, Any]:
    """Disable a plugin (removes its skills from the registry)."""
    manager = _get_manager(request)
    if manager is None:
        return {"success": False, "error": "Plugin system not available"}
    success = manager.disable(name)
    return {"success": success, "plugins": manager.status()}
