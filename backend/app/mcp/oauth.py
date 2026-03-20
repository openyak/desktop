"""OAuth 2.1 client for MCP remote servers.

Implements the authorization code flow with PKCE as specified by the
MCP authorization spec (draft).  The flow is:

1. Discover auth server metadata from the MCP server URL
2. Build an authorization URL for the user to visit
3. Exchange the returned auth code for tokens
4. Refresh tokens when they expire
"""

from __future__ import annotations

import base64
import hashlib
import logging
import secrets
import time
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlencode, urlparse

import httpx

logger = logging.getLogger(__name__)

_TIMEOUT = 15  # seconds for HTTP requests


@dataclass
class AuthServerMeta:
    """Metadata about an OAuth authorization server."""

    authorization_endpoint: str
    token_endpoint: str
    scopes: list[str] = field(default_factory=list)
    resource_url: str = ""  # the MCP server URL this auth is for
    registration_endpoint: str = ""  # RFC 7591 dynamic client registration
    client_id_metadata_document_supported: bool = False


@dataclass
class TokenSet:
    """OAuth token set."""

    access_token: str
    refresh_token: str | None = None
    expires_at: float = 0.0  # unix timestamp
    token_type: str = "Bearer"
    scope: str = ""

    @property
    def expired(self) -> bool:
        if self.expires_at <= 0:
            return False  # no expiry info — assume valid
        return time.time() >= self.expires_at - 60  # 60s buffer


@dataclass
class PendingAuth:
    """State for an in-progress OAuth flow."""

    server_name: str
    mcp_url: str
    auth_meta: AuthServerMeta
    pkce_verifier: str
    state: str
    redirect_uri: str
    client_id: str = ""


def generate_pkce_pair() -> tuple[str, str]:
    """Generate PKCE code_verifier and code_challenge (S256)."""
    verifier = secrets.token_urlsafe(64)[:128]
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return verifier, challenge


async def discover_auth_server(mcp_url: str) -> AuthServerMeta | None:
    """Discover the OAuth authorization server for an MCP endpoint.

    1. Send an unauthenticated request to the MCP server
    2. Parse the 401 response for WWW-Authenticate header
    3. Fetch Protected Resource Metadata (RFC 9728)
    4. Fetch Authorization Server Metadata (RFC 8414)
    """
    async with httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=True) as client:
        # Step 1: Probe the MCP server
        try:
            resp = await client.post(
                mcp_url,
                json={"jsonrpc": "2.0", "method": "initialize", "id": 1, "params": {}},
                headers={"Content-Type": "application/json", "Accept": "application/json"},
            )
        except httpx.HTTPError as e:
            logger.debug("MCP probe failed for %s: %s", mcp_url, e)
            return None

        if resp.status_code not in (401, 403):
            logger.debug("MCP server %s returned %d (not 401), may not need auth", mcp_url, resp.status_code)
            return None

        # Step 2: Parse WWW-Authenticate header
        www_auth = resp.headers.get("www-authenticate", "")
        resource_metadata_url = _extract_resource_metadata_url(www_auth, mcp_url)

        # Step 3: Fetch Protected Resource Metadata
        auth_server_url = None
        scopes: list[str] = []

        if resource_metadata_url:
            try:
                rm_resp = await client.get(resource_metadata_url)
                if rm_resp.status_code == 200:
                    rm_data = rm_resp.json()
                    auth_servers = rm_data.get("authorization_servers", [])
                    if auth_servers:
                        auth_server_url = auth_servers[0]
                    scopes = rm_data.get("scopes_supported", [])
            except Exception as e:
                logger.debug("Failed to fetch resource metadata: %s", e)

        # Fallback: derive auth server URL from MCP URL
        if not auth_server_url:
            parsed = urlparse(mcp_url)
            auth_server_url = f"{parsed.scheme}://{parsed.netloc}"

        # Step 4: Fetch Authorization Server Metadata (RFC 8414)
        as_meta_url = f"{auth_server_url.rstrip('/')}/.well-known/oauth-authorization-server"
        try:
            as_resp = await client.get(as_meta_url)
            if as_resp.status_code == 200:
                as_data = as_resp.json()
                return AuthServerMeta(
                    authorization_endpoint=as_data.get("authorization_endpoint", ""),
                    token_endpoint=as_data.get("token_endpoint", ""),
                    scopes=scopes or as_data.get("scopes_supported", []),
                    resource_url=mcp_url,
                    registration_endpoint=as_data.get("registration_endpoint", ""),
                    client_id_metadata_document_supported=as_data.get(
                        "client_id_metadata_document_supported", False
                    ),
                )
        except Exception as e:
            logger.debug("Failed to fetch auth server metadata from %s: %s", as_meta_url, e)

        # Try OpenID Connect discovery as fallback
        oidc_url = f"{auth_server_url.rstrip('/')}/.well-known/openid-configuration"
        try:
            oidc_resp = await client.get(oidc_url)
            if oidc_resp.status_code == 200:
                oidc_data = oidc_resp.json()
                return AuthServerMeta(
                    authorization_endpoint=oidc_data.get("authorization_endpoint", ""),
                    token_endpoint=oidc_data.get("token_endpoint", ""),
                    scopes=scopes or oidc_data.get("scopes_supported", []),
                    resource_url=mcp_url,
                    registration_endpoint=oidc_data.get("registration_endpoint", ""),
                    client_id_metadata_document_supported=oidc_data.get(
                        "client_id_metadata_document_supported", False
                    ),
                )
        except Exception as e:
            logger.debug("Failed to fetch OIDC metadata from %s: %s", oidc_url, e)

    return None


def build_authorization_url(
    auth_meta: AuthServerMeta,
    redirect_uri: str,
    state: str,
    code_challenge: str,
    client_id: str = "",
    extra_params: dict[str, str] | None = None,
) -> str:
    """Build the OAuth authorization URL for the user to visit."""
    params: dict[str, str] = {
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    if client_id:
        params["client_id"] = client_id
    if auth_meta.scopes:
        params["scope"] = " ".join(auth_meta.scopes)
    if auth_meta.resource_url:
        params["resource"] = auth_meta.resource_url
    if extra_params:
        params.update(extra_params)

    return f"{auth_meta.authorization_endpoint}?{urlencode(params)}"


async def exchange_code(
    auth_meta: AuthServerMeta,
    code: str,
    redirect_uri: str,
    pkce_verifier: str,
    client_id: str = "",
) -> TokenSet:
    """Exchange an authorization code for tokens."""
    data: dict[str, str] = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "code_verifier": pkce_verifier,
    }
    if client_id:
        data["client_id"] = client_id

    logger.info("Token exchange → %s (client_id=%s)", auth_meta.token_endpoint, client_id[:20] if client_id else "<none>")

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.post(
            auth_meta.token_endpoint,
            data=data,
            headers={"Accept": "application/json"},
        )
        if resp.status_code >= 400:
            logger.warning("Token endpoint returned %d: %s", resp.status_code, resp.text[:500])
        resp.raise_for_status()
        body = resp.json()

    expires_in = body.get("expires_in", 0)
    return TokenSet(
        access_token=body["access_token"],
        refresh_token=body.get("refresh_token"),
        expires_at=time.time() + expires_in if expires_in else 0,
        token_type=body.get("token_type", "Bearer"),
        scope=body.get("scope", ""),
    )


async def refresh_token(
    auth_meta: AuthServerMeta,
    current_refresh_token: str,
    client_id: str = "",
) -> TokenSet:
    """Refresh an expired access token."""
    data: dict[str, str] = {
        "grant_type": "refresh_token",
        "refresh_token": current_refresh_token,
    }
    if client_id:
        data["client_id"] = client_id

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.post(
            auth_meta.token_endpoint,
            data=data,
            headers={"Accept": "application/json"},
        )
        resp.raise_for_status()
        body = resp.json()

    expires_in = body.get("expires_in", 0)
    return TokenSet(
        access_token=body["access_token"],
        refresh_token=body.get("refresh_token", current_refresh_token),
        expires_at=time.time() + expires_in if expires_in else 0,
        token_type=body.get("token_type", "Bearer"),
        scope=body.get("scope", ""),
    )


async def register_client(
    auth_meta: AuthServerMeta,
    redirect_uris: list[str],
    client_name: str = "OpenYak",
) -> str | None:
    """Dynamically register an OAuth client (RFC 7591).

    Returns the ``client_id`` on success, or ``None`` on failure.
    """
    if not auth_meta.registration_endpoint:
        return None

    body = {
        "client_name": client_name,
        "redirect_uris": redirect_uris,
        "grant_types": ["authorization_code", "refresh_token"],
        "response_types": ["code"],
        "token_endpoint_auth_method": "none",  # public client (PKCE)
    }

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        try:
            resp = await client.post(
                auth_meta.registration_endpoint,
                json=body,
                headers={"Accept": "application/json", "Content-Type": "application/json"},
            )
            if resp.status_code in (200, 201):
                data = resp.json()
                client_id = data.get("client_id", "")
                if client_id:
                    logger.info(
                        "Registered OAuth client '%s' at %s",
                        client_id, auth_meta.registration_endpoint,
                    )
                    return client_id
            else:
                logger.warning(
                    "Dynamic client registration failed (%d): %s",
                    resp.status_code, resp.text[:200],
                )
        except Exception as e:
            logger.warning("Dynamic client registration error: %s", e)

    return None


def _extract_resource_metadata_url(www_auth: str, mcp_url: str) -> str | None:
    """Extract resource_metadata URL from WWW-Authenticate header.

    Format: Bearer resource_metadata="https://..."
    """
    if "resource_metadata=" in www_auth:
        for part in www_auth.split(","):
            part = part.strip()
            if "resource_metadata=" in part:
                url = part.split("resource_metadata=", 1)[1].strip().strip('"')
                return url

    # Fallback: try well-known URI based on MCP server URL
    parsed = urlparse(mcp_url)
    return f"{parsed.scheme}://{parsed.netloc}/.well-known/oauth-protected-resource"
