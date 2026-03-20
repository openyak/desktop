"""OpenAI OAuth PKCE token manager.

Handles the OAuth 2.0 + PKCE flow for ChatGPT subscription access,
including token exchange, refresh, and JWT decoding for account ID.

Reference: 7shi/codex-oauth (Python, ~250 lines).
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import logging
import os
import time

import httpx

logger = logging.getLogger(__name__)

_refresh_lock = asyncio.Lock()

# OpenAI OAuth constants (public Client ID shared by Codex CLI community)
AUTH_URL = "https://auth.openai.com/oauth/authorize"
TOKEN_URL = "https://auth.openai.com/oauth/token"
CLIENT_ID = "app_EMoamEEZ73f0CkXaXp7hrann"
SCOPES = "openid profile email offline_access"
AUDIENCE = "https://api.openai.com/v1"


def generate_auth_url(redirect_uri: str, state: str) -> tuple[str, str]:
    """Generate an OAuth authorization URL with PKCE S256.

    Returns (auth_url, code_verifier).
    """
    # PKCE: generate code_verifier and code_challenge
    code_verifier = base64.urlsafe_b64encode(os.urandom(32)).rstrip(b"=").decode()
    code_challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode()).digest())
        .rstrip(b"=")
        .decode()
    )

    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": SCOPES,
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "id_token_add_organizations": "true",
        "codex_cli_simplified_flow": "true",
        "originator": "codex",
    }

    # Use httpx to properly encode
    url = str(httpx.URL(AUTH_URL).copy_merge_params(params))

    return url, code_verifier


async def exchange_code(
    code: str,
    redirect_uri: str,
    code_verifier: str,
) -> dict:
    """Exchange authorization code for tokens.

    Returns dict with: access_token, refresh_token, id_token, expires_in.
    """
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "client_id": CLIENT_ID,
                "code": code,
                "redirect_uri": redirect_uri,
                "code_verifier": code_verifier,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=15.0,
        )

    if resp.status_code != 200:
        logger.error("Token exchange failed: HTTP %d — %s", resp.status_code, resp.text[:300])
        raise RuntimeError(f"Token exchange failed: HTTP {resp.status_code}")

    return resp.json()


async def refresh_access_token(refresh_token: str) -> dict:
    """Refresh an expired access token.

    Returns dict with: access_token, refresh_token (rotated), expires_in.
    Thread-safe: concurrent callers wait on a single refresh attempt.
    """
    async with _refresh_lock:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                TOKEN_URL,
                data={
                    "grant_type": "refresh_token",
                    "client_id": CLIENT_ID,
                    "refresh_token": refresh_token,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=15.0,
            )

        if resp.status_code != 200:
            logger.error(
                "OpenAI token refresh failed: HTTP %d — %s",
                resp.status_code,
                resp.text[:300],
            )
            raise RuntimeError(f"Token refresh failed: HTTP {resp.status_code}")

        return resp.json()


def extract_account_id(id_token: str) -> str:
    """Decode a JWT id_token (without verification) to extract chatgpt_account_id.

    Uses a multi-tier fallback: top-level auth claim → organizations[0] →
    org ID → top-level JWT claim.
    """
    parts = id_token.split(".")
    if len(parts) < 2:
        raise ValueError("Invalid JWT: expected at least 2 parts")

    payload_b64 = parts[1]
    payload_b64 += "=" * (4 - len(payload_b64) % 4)
    payload = json.loads(base64.urlsafe_b64decode(payload_b64))

    auth_info = payload.get("https://api.openai.com/auth", {})
    logger.debug("id_token auth claim keys: %s", list(auth_info.keys()))

    # Tier 1: Top level of auth claim (most common for ChatGPT Plus/Pro)
    account_id = auth_info.get("chatgpt_account_id", "")
    if account_id:
        return account_id

    # Tier 2: Inside organizations[0] (some account types)
    organizations = auth_info.get("organizations", [])
    if organizations:
        account_id = organizations[0].get("chatgpt_account_id", "")
        if account_id:
            return account_id
        # Tier 3: Org ID as fallback
        account_id = organizations[0].get("id", "")
        if account_id:
            return account_id

    # Tier 4: Top-level JWT claim
    account_id = payload.get("chatgpt_account_id", "")
    if account_id:
        return account_id

    raise ValueError("No chatgpt_account_id found in id_token")


def extract_email(id_token: str) -> str:
    """Decode a JWT id_token to extract the user's email."""
    parts = id_token.split(".")
    if len(parts) < 2:
        return ""

    payload_b64 = parts[1]
    payload_b64 += "=" * (4 - len(payload_b64) % 4)
    try:
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
        return payload.get("email", "")
    except Exception:
        return ""


def is_token_expired(expires_at_ms: int, buffer_seconds: int = 300) -> bool:
    """Check if a token is expired or about to expire within buffer_seconds."""
    now_ms = int(time.time() * 1000)
    return now_ms >= (expires_at_ms - buffer_seconds * 1000)
