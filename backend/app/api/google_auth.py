"""Google Workspace OAuth — direct Google OAuth flow for Gmail/Calendar/Drive.

Unlike remote MCP connectors (Notion, Slack) that handle OAuth via MCP protocol,
Google Workspace requires us to manage Google OAuth directly because Google
doesn't provide a hosted MCP endpoint for consumer Workspace products.

Flow:
  1. User clicks Connect on Google Workspace connector
  2. We redirect to Google OAuth consent screen (using our client_id)
  3. User authorizes
  4. Google redirects to our callback
  5. We exchange code for tokens, store them
  6. We restart the google-workspace MCP server with injected tokens
"""

from __future__ import annotations

import json
import logging
import secrets
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/google")

# Google OAuth endpoints
_GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
_GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"

# Scopes for Gmail + Calendar + Drive
_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/drive.readonly",
]

# In-memory pending states
_pending_states: dict[str, dict[str, str]] = {}


def _get_token_path(project_dir: str | None) -> Path:
    """Where to store Google OAuth tokens."""
    if project_dir:
        return Path(project_dir).resolve() / ".openyak" / "google-tokens.json"
    return Path.home() / ".openyak" / "google-tokens.json"


def load_google_tokens(project_dir: str | None) -> dict[str, Any] | None:
    """Load stored Google tokens from disk."""
    path = _get_token_path(project_dir)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except (OSError, json.JSONDecodeError):
        return None


def _save_tokens(project_dir: str | None, tokens: dict[str, Any]) -> None:
    path = _get_token_path(project_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(tokens, indent=2), encoding="utf-8")


@router.post("/auth-start")
async def google_auth_start(request: Request) -> dict[str, Any]:
    """Start Google OAuth flow. Returns auth URL to open in browser."""
    settings = request.app.state.settings

    if not settings.google_client_id:
        return {"success": False, "error": "Google OAuth not configured (missing OPENYAK_GOOGLE_CLIENT_ID)"}

    host = settings.host if settings.host != "0.0.0.0" else "localhost"
    redirect_uri = f"http://{host}:{settings.port}/api/google/callback"

    state = secrets.token_urlsafe(32)
    _pending_states[state] = {"redirect_uri": redirect_uri}

    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(_SCOPES),
        "access_type": "offline",  # get refresh_token
        "prompt": "consent",  # force consent to get refresh_token
        "state": state,
    }

    auth_url = f"{_GOOGLE_AUTH_URL}?{urlencode(params)}"
    return {"success": True, "auth_url": auth_url, "state": state}


@router.get("/callback")
async def google_callback(code: str, state: str, request: Request):
    """Google OAuth callback — exchange code for tokens."""
    settings = request.app.state.settings

    pending = _pending_states.pop(state, None)
    if not pending:
        return HTMLResponse("<p>Invalid state. Please try again.</p>")

    redirect_uri = pending["redirect_uri"]

    # Exchange code for tokens
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                _GOOGLE_TOKEN_URL,
                data={
                    "code": code,
                    "client_id": settings.google_client_id,
                    "client_secret": settings.google_client_secret,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
            if resp.status_code != 200:
                logger.warning("Google token exchange failed: %d %s", resp.status_code, resp.text[:300])
                return HTMLResponse(f"<p>Token exchange failed: {resp.status_code}</p>")

            token_data = resp.json()
    except Exception as e:
        logger.warning("Google token exchange error: %s", e)
        return HTMLResponse(f"<p>Error: {e}</p>")

    # Store tokens
    tokens = {
        "access_token": token_data["access_token"],
        "refresh_token": token_data.get("refresh_token", ""),
        "expires_at": time.time() + token_data.get("expires_in", 3600),
        "token_type": token_data.get("token_type", "Bearer"),
        "scope": token_data.get("scope", ""),
    }
    _save_tokens(settings.project_dir, tokens)
    logger.warning("[Google OAuth] Tokens stored successfully!")

    # Restart google-workspace connector with fresh credentials
    connector_registry = getattr(request.app.state, "connector_registry", None)
    if connector_registry:
        connector_registry._inject_local_credentials()
        try:
            await connector_registry.reconnect("google-workspace")
        except Exception as e:
            logger.warning("Failed to reconnect google-workspace: %s", e)

    from app.api.callback_html import render_callback
    return HTMLResponse(content=render_callback(
        True,
        extra_data={"connector": "google-workspace"},
    ))


@router.get("/status")
async def google_status(request: Request) -> dict[str, Any]:
    """Check if Google tokens are stored."""
    settings = request.app.state.settings
    tokens = load_google_tokens(settings.project_dir)
    if not tokens:
        return {"connected": False}

    expired = tokens.get("expires_at", 0) < time.time()
    return {
        "connected": True,
        "expired": expired,
        "scope": tokens.get("scope", ""),
        "has_refresh": bool(tokens.get("refresh_token")),
    }
