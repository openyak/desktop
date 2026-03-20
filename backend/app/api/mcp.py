"""MCP server management endpoints (legacy — delegates to ConnectorRegistry).

New code should use /api/connectors/ endpoints instead.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter(prefix="/mcp")


def _get_registry(request: Request):
    return getattr(request.app.state, "connector_registry", None)


def _get_manager(request: Request):
    """Backward compat: try connector_registry first, then mcp_manager."""
    registry = _get_registry(request)
    if registry and registry.mcp_manager:
        return registry.mcp_manager
    return getattr(request.app.state, "mcp_manager", None)


@router.get("/status")
async def mcp_status(request: Request) -> dict[str, Any]:
    """Return status of all configured MCP servers."""
    registry = _get_registry(request)
    if registry:
        return {"servers": registry.status()}
    manager = _get_manager(request)
    if manager is None:
        return {"servers": {}}
    return {"servers": manager.status()}


@router.post("/{name}/reconnect")
async def mcp_reconnect(name: str, request: Request) -> dict[str, Any]:
    """Reconnect a specific MCP server."""
    registry = _get_registry(request)
    if registry:
        success = await registry.reconnect(name)
        return {"success": success, "servers": registry.status()}
    manager = _get_manager(request)
    if manager is None:
        return {"success": False, "error": "MCP not configured"}
    success = await manager.reconnect(name)
    return {"success": success, "servers": manager.status()}


# ------------------------------------------------------------------
# OAuth endpoints (delegate to connector_registry or mcp_manager)
# ------------------------------------------------------------------


class AuthCallbackBody(BaseModel):
    code: str
    state: str


@router.post("/{name}/auth-start")
async def mcp_auth_start(name: str, request: Request) -> dict[str, Any]:
    """Start an OAuth flow for an MCP server."""
    registry = _get_registry(request)
    settings = request.app.state.settings
    host = settings.host if settings.host != "0.0.0.0" else "localhost"
    redirect_uri = f"http://{host}:{settings.port}/api/connectors/oauth/callback"

    if registry:
        result = await registry.connect(name, redirect_uri)
    else:
        manager = _get_manager(request)
        if manager is None:
            return {"success": False, "error": "MCP not configured"}
        result = await manager.start_auth(name, redirect_uri)

    if result is None:
        return {
            "success": False,
            "error": "Could not discover OAuth server for this MCP endpoint",
        }
    return {"success": True, **result}


@router.get("/oauth/callback")
async def mcp_oauth_callback(
    code: str, state: str, request: Request
) -> dict[str, Any]:
    """OAuth callback endpoint — receives auth code from provider."""
    registry = _get_registry(request)
    if registry:
        success = await registry.complete_auth(state, code)
    else:
        manager = _get_manager(request)
        if manager is None:
            return {"success": False, "error": "MCP not configured"}
        success = await manager.complete_auth(state, code)

    from fastapi.responses import HTMLResponse
    from app.api.callback_html import render_callback
    return HTMLResponse(content=render_callback(
        success,
        message_type="mcp-auth-complete",
        extra_data={"state": state},
    ))


@router.post("/{name}/auth-callback")
async def mcp_auth_callback_api(
    name: str, body: AuthCallbackBody, request: Request
) -> dict[str, Any]:
    """API-based auth callback."""
    registry = _get_registry(request)
    if registry:
        success = await registry.complete_auth(body.state, body.code)
        return {"success": success, "servers": registry.status()}
    manager = _get_manager(request)
    if manager is None:
        return {"success": False, "error": "MCP not configured"}
    success = await manager.complete_auth(body.state, body.code)
    return {"success": success, "servers": manager.status()}


@router.post("/{name}/disconnect")
async def mcp_disconnect(name: str, request: Request) -> dict[str, Any]:
    """Remove stored OAuth tokens and disconnect an MCP server."""
    registry = _get_registry(request)
    if registry:
        success = await registry.disconnect(name)
        return {"success": success, "servers": registry.status()}
    manager = _get_manager(request)
    if manager is None:
        return {"success": False, "error": "MCP not configured"}
    success = await manager.disconnect_auth(name)
    return {"success": success, "servers": manager.status()}
