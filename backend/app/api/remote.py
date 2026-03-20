"""Remote access management API — enable/disable, QR code, status, task list.

All management endpoints are localhost-only. The regular /api/chat/* endpoints
handle the actual remote task execution (protected by RemoteAuthMiddleware).
"""

from __future__ import annotations

import io
import json
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel

from app.auth.token import (
    delete_token,
    generate_token,
    load_token,
    rotate_token,
    save_token,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/remote", tags=["remote"])


# --- Localhost guard ---

def _localhost_only(request: Request) -> None:
    """Dependency that rejects non-localhost requests."""
    client_ip = request.client.host if request.client else "unknown"
    if client_ip not in ("127.0.0.1", "::1", "localhost"):
        raise HTTPException(status_code=403, detail="This endpoint is only accessible from localhost")


# --- Schemas ---

class RemoteEnableResponse(BaseModel):
    token: str
    tunnel_url: str | None = None


class RemoteStatusResponse(BaseModel):
    enabled: bool
    tunnel_url: str | None = None
    token_preview: str | None = None  # First 12 chars
    active_tasks: int = 0
    tunnel_mode: str = "cloudflare"
    permission_mode: str = "auto"
    active_providers: list[str] = []  # e.g. ["openai-subscription", "openrouter"]


class RemoteConfigUpdate(BaseModel):
    permission_mode: str | None = None  # "auto" | "ask" | "deny"
    tunnel_mode: str | None = None  # "cloudflare" | "manual"
    tunnel_url: str | None = None  # For manual mode


# --- Endpoints ---

@router.post("/enable", response_model=RemoteEnableResponse, dependencies=[Depends(_localhost_only)])
async def enable_remote(request: Request) -> RemoteEnableResponse:
    """Enable remote access: generate token and start tunnel."""
    settings = request.app.state.settings
    token_path = Path(settings.remote_token_path)

    # Generate token if not exists
    token = load_token(token_path)
    if not token:
        token = generate_token()
        save_token(token, token_path)

    # Update settings
    settings.remote_access_enabled = True

    # Start tunnel if not already running
    tunnel_url = None
    if settings.remote_tunnel_mode == "cloudflare":
        tunnel_mgr = getattr(request.app.state, "tunnel_manager", None)
        if tunnel_mgr is None:
            from app.auth.tunnel import TunnelManager
            tunnel_mgr = TunnelManager(backend_port=settings.port)
            request.app.state.tunnel_manager = tunnel_mgr

        if not tunnel_mgr.is_running:
            try:
                tunnel_url = await tunnel_mgr.start()
            except Exception as e:
                logger.error("Failed to start tunnel: %s", e)
                raise HTTPException(status_code=500, detail=f"Failed to start tunnel: {e}")
        else:
            tunnel_url = tunnel_mgr.tunnel_url
    elif settings.remote_tunnel_mode == "manual":
        tunnel_url = settings.remote_tunnel_url or None

    return RemoteEnableResponse(token=token, tunnel_url=tunnel_url)


@router.post("/disable", dependencies=[Depends(_localhost_only)])
async def disable_remote(request: Request) -> dict:
    """Disable remote access: revoke token and stop tunnel."""
    settings = request.app.state.settings
    token_path = Path(settings.remote_token_path)

    # Revoke token
    delete_token(token_path)

    # Stop tunnel
    tunnel_mgr = getattr(request.app.state, "tunnel_manager", None)
    if tunnel_mgr:
        await tunnel_mgr.stop()

    settings.remote_access_enabled = False

    return {"status": "disabled"}


@router.get("/status", response_model=RemoteStatusResponse, dependencies=[Depends(_localhost_only)])
async def remote_status(request: Request) -> RemoteStatusResponse:
    """Get remote access status."""
    settings = request.app.state.settings
    token_path = Path(settings.remote_token_path)

    token = load_token(token_path)
    tunnel_mgr = getattr(request.app.state, "tunnel_manager", None)

    # Count active tasks
    sm = getattr(request.app.state, "stream_manager", None)
    active_tasks = len(sm.active_jobs()) if sm else 0

    tunnel_url = None
    if tunnel_mgr and tunnel_mgr.is_running:
        tunnel_url = tunnel_mgr.tunnel_url
    elif settings.remote_tunnel_mode == "manual":
        tunnel_url = settings.remote_tunnel_url or None

    # List registered providers (those with API keys/tokens configured)
    registry = getattr(request.app.state, "provider_registry", None)
    active_providers = list(registry._providers.keys()) if registry else []

    return RemoteStatusResponse(
        enabled=settings.remote_access_enabled,
        tunnel_url=tunnel_url,
        token_preview=token[:16] + "..." if token else None,
        active_tasks=active_tasks,
        tunnel_mode=settings.remote_tunnel_mode,
        permission_mode=settings.remote_permission_mode,
        active_providers=active_providers,
    )


@router.get("/qr", dependencies=[Depends(_localhost_only)])
async def remote_qr(request: Request) -> Response:
    """Generate QR code PNG encoding the connection info {url, token}."""
    settings = request.app.state.settings
    token_path = Path(settings.remote_token_path)

    token = load_token(token_path)
    if not token:
        raise HTTPException(status_code=400, detail="Remote access not enabled — no token")

    # Determine tunnel URL
    tunnel_url = None
    tunnel_mgr = getattr(request.app.state, "tunnel_manager", None)
    if tunnel_mgr and tunnel_mgr.is_running:
        tunnel_url = tunnel_mgr.tunnel_url
    elif settings.remote_tunnel_mode == "manual":
        tunnel_url = settings.remote_tunnel_url

    if not tunnel_url:
        raise HTTPException(status_code=400, detail="No tunnel URL available")

    # QR payload: direct URL with token — scannable by any phone QR reader
    qr_data = f"{tunnel_url}/m?token={token}"

    try:
        import qrcode
        from qrcode.image.pil import PilImage

        qr = qrcode.QRCode(version=None, box_size=8, border=2)
        qr.add_data(qr_data)
        qr.make(fit=True)
        img: PilImage = qr.make_image(fill_color="white", back_color="black")

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)

        return StreamingResponse(buf, media_type="image/png")
    except ImportError:
        # Fallback: return the QR data as JSON (frontend can render it)
        return Response(
            content=qr_data,
            media_type="application/json",
            headers={"X-QR-Fallback": "true"},
        )


@router.get("/provider-info")
async def provider_info(request: Request) -> dict:
    """Return which providers are configured on the desktop.

    Accessible from remote clients (phone) — protected by auth middleware.
    Used by mobile to auto-detect which provider the desktop has active.
    """
    registry = getattr(request.app.state, "provider_registry", None)
    providers = list(registry._providers.keys()) if registry else []

    # Determine the "primary" provider: prefer subscription over API-key
    primary = None
    if "openai-subscription" in providers:
        primary = "chatgpt"
    elif "openrouter" in providers:
        primary = "openrouter"

    return {
        "providers": providers,  # e.g. ["openrouter", "openai-subscription"]
        "primary": primary,  # "chatgpt" | "openrouter" | null
    }


@router.post("/rotate-token", dependencies=[Depends(_localhost_only)])
async def rotate_remote_token(request: Request) -> dict:
    """Generate a new token, invalidating the old one."""
    settings = request.app.state.settings
    token_path = Path(settings.remote_token_path)

    new_token = rotate_token(token_path)
    return {"token": new_token, "token_preview": new_token[:16] + "..."}


@router.patch("/config", dependencies=[Depends(_localhost_only)])
async def update_remote_config(request: Request, body: RemoteConfigUpdate) -> dict:
    """Update remote access configuration."""
    settings = request.app.state.settings

    if body.permission_mode is not None:
        if body.permission_mode not in ("auto", "ask", "deny"):
            raise HTTPException(status_code=400, detail="Invalid permission_mode")
        settings.remote_permission_mode = body.permission_mode

    if body.tunnel_mode is not None:
        if body.tunnel_mode not in ("cloudflare", "manual"):
            raise HTTPException(status_code=400, detail="Invalid tunnel_mode")
        settings.remote_tunnel_mode = body.tunnel_mode

    if body.tunnel_url is not None:
        settings.remote_tunnel_url = body.tunnel_url

    return {"status": "updated"}


@router.get("/tasks", dependencies=[Depends(_localhost_only)])
async def list_remote_tasks(request: Request) -> list[dict]:
    """List recent tasks with status summary (for mobile task list)."""
    sm = getattr(request.app.state, "stream_manager", None)
    if not sm:
        return []

    tasks = []
    for stream_id, job in sm._jobs.items():
        status = "completed" if job.completed else "running"
        # Check if waiting for permission
        if not job.completed and job._response_futures:
            status = "waiting_permission"
        tasks.append({
            "stream_id": stream_id,
            "session_id": job.session_id,
            "status": status,
        })

    return tasks
