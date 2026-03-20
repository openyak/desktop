"""MCP manager — lifecycle management for all configured MCP servers."""

from __future__ import annotations

import logging
import secrets
from typing import Any

from app.mcp.client import McpClient
from app.mcp.oauth import (
    AuthServerMeta,
    PendingAuth,
    build_authorization_url,
    discover_auth_server,
    exchange_code,
    generate_pkce_pair,
    refresh_token,
)
from app.mcp.token_store import McpTokenStore
from app.mcp.tool_wrapper import McpToolWrapper
from app.tool.base import ToolDefinition

logger = logging.getLogger(__name__)


class McpManager:
    """Manages all MCP server connections and exposes their tools."""

    def __init__(
        self,
        mcp_config: dict[str, Any],
        project_dir: str | None = None,
    ) -> None:
        self._config = mcp_config
        self._clients: dict[str, McpClient] = {}
        self._token_store = McpTokenStore(project_dir)
        self._pending_auths: dict[str, PendingAuth] = {}  # keyed by state param

    async def startup(self) -> None:
        """Connect to all enabled MCP servers."""
        for name, config in self._config.items():
            if not isinstance(config, dict):
                continue
            if not config.get("enabled", True):
                logger.info("MCP server '%s' is disabled, skipping", name)
                continue

            client = McpClient(name, config)

            # Inject stored OAuth token if available
            stored = self._token_store.get(name)
            if stored and not stored.expired:
                client.set_oauth_token(stored.access_token)
            elif stored and stored.expired and stored.refresh_token:
                # Try to refresh
                auth_meta = self._token_store.get_auth_meta(name)
                if auth_meta:
                    try:
                        new_tokens = await refresh_token(auth_meta, stored.refresh_token)
                        self._token_store.save(name, new_tokens, auth_meta)
                        client.set_oauth_token(new_tokens.access_token)
                        logger.info("Refreshed OAuth token for MCP server '%s'", name)
                    except Exception as e:
                        logger.warning("Token refresh failed for '%s': %s", name, e)

            await client.connect()

            # If connection failed and it's a remote server without a token,
            # mark as needs_auth instead of failed
            if (
                client.status == "failed"
                and client.server_type != "local"
                and not client._oauth_token
            ):
                client.status = "needs_auth"
                client.error = None

            self._clients[name] = client

        connected = sum(1 for c in self._clients.values() if c.status == "connected")
        total = len(self._clients)
        logger.info("MCP startup complete: %d/%d servers connected", connected, total)

    async def shutdown(self) -> None:
        """Disconnect from all MCP servers."""
        for client in self._clients.values():
            try:
                await client.close()
            except Exception:
                logger.exception("Error closing MCP server '%s'", client.name)
        self._clients.clear()

    def tools(self) -> list[ToolDefinition]:
        """Get all tools from connected MCP servers as ToolDefinitions."""
        result: list[ToolDefinition] = []
        for client in self._clients.values():
            if client.status != "connected":
                continue
            for mcp_tool in client.list_tools():
                wrapper = McpToolWrapper(client, mcp_tool)
                result.append(wrapper)
        return result

    def status(self) -> dict[str, dict[str, Any]]:
        """Return status of all MCP servers."""
        return {
            name: {
                "status": client.status,
                "error": client.error,
                "type": client.server_type,
                "tools": len(client.list_tools()),
            }
            for name, client in self._clients.items()
        }

    async def reconnect(self, name: str) -> bool:
        """Reconnect a specific MCP server. Returns True if successful."""
        client = self._clients.get(name)
        if client is None:
            config = self._config.get(name)
            if not isinstance(config, dict):
                return False
            client = McpClient(name, config)
            self._clients[name] = client

        # Re-inject stored token (or try refresh)
        stored = self._token_store.get(name)
        if stored and not stored.expired:
            client.set_oauth_token(stored.access_token)
        elif stored and stored.expired and stored.refresh_token:
            auth_meta = self._token_store.get_auth_meta(name)
            if auth_meta:
                try:
                    new_tokens = await refresh_token(auth_meta, stored.refresh_token)
                    self._token_store.save(name, new_tokens, auth_meta)
                    client.set_oauth_token(new_tokens.access_token)
                    logger.info("Refreshed OAuth token for '%s' on reconnect", name)
                except Exception as e:
                    logger.warning("Token refresh failed for '%s': %s", name, e)

        await client.close()
        await client.connect()

        # If remote server failed without a token → mark needs_auth
        if (
            client.status == "failed"
            and client.server_type != "local"
            and not client._oauth_token
        ):
            client.status = "needs_auth"
            client.error = None

        return client.status == "connected"

    # ------------------------------------------------------------------
    # OAuth flow
    # ------------------------------------------------------------------

    async def start_auth(
        self, name: str, redirect_uri: str
    ) -> dict[str, str] | None:
        """Start an OAuth flow for a server. Returns auth URL + state, or None."""
        config = self._config.get(name)
        if not isinstance(config, dict):
            return None

        url = config.get("url", "")
        if not url:
            return None

        # Discover auth server
        auth_meta = await discover_auth_server(url)
        if not auth_meta or not auth_meta.authorization_endpoint:
            return None

        # Obtain client_id: stored → DCR → fallback probe
        client_id = self._token_store.get_client_id(name) or ""

        if not client_id:
            # Try Dynamic Client Registration (RFC 7591)
            reg_endpoint = auth_meta.registration_endpoint
            if not reg_endpoint:
                # Some servers support DCR but don't advertise it — try common paths
                from urllib.parse import urlparse
                parsed = urlparse(auth_meta.authorization_endpoint)
                reg_endpoint = f"{parsed.scheme}://{parsed.netloc}/register"

            if reg_endpoint:
                from app.mcp.oauth import register_client as _register
                client_id = await _register(
                    AuthServerMeta(
                        authorization_endpoint=auth_meta.authorization_endpoint,
                        token_endpoint=auth_meta.token_endpoint,
                        scopes=auth_meta.scopes,
                        resource_url=auth_meta.resource_url,
                        registration_endpoint=reg_endpoint,
                    ),
                    redirect_uris=[redirect_uri],
                ) or ""
                if client_id:
                    self._token_store.save_client_id(name, client_id)
                    logger.warning("[OAuth] Registered client_id for '%s': %s", name, client_id[:20])

        if not client_id:
            logger.warning("[OAuth] No client_id for '%s' — auth may fail (server may not support DCR)", name)

        # Generate PKCE + state
        verifier, challenge = generate_pkce_pair()
        state = secrets.token_urlsafe(32)

        # Build authorization URL
        auth_url = build_authorization_url(
            auth_meta=auth_meta,
            redirect_uri=redirect_uri,
            state=state,
            code_challenge=challenge,
            client_id=client_id,
        )

        # Store pending auth
        self._pending_auths[state] = PendingAuth(
            server_name=name,
            mcp_url=url,
            auth_meta=auth_meta,
            pkce_verifier=verifier,
            state=state,
            redirect_uri=redirect_uri,
            client_id=client_id,
        )

        return {"auth_url": auth_url, "state": state}

    async def complete_auth(self, state: str, code: str) -> bool:
        """Complete an OAuth flow with the auth code. Returns True if successful."""
        logger.warning("[OAuth] complete_auth called (state=%s..., %d pending)", state[:8], len(self._pending_auths))
        pending = self._pending_auths.pop(state, None)
        if not pending:
            logger.warning("[OAuth] No pending auth found for state=%s (keys: %s)", state[:8], list(self._pending_auths.keys())[:3])
            return False

        logger.warning(
            "[OAuth] Exchanging code for '%s' (client_id=%s, redirect=%s, token_ep=%s)",
            pending.server_name,
            pending.client_id[:20] if pending.client_id else "<none>",
            pending.redirect_uri,
            pending.auth_meta.token_endpoint,
        )
        try:
            tokens = await exchange_code(
                auth_meta=pending.auth_meta,
                code=code,
                redirect_uri=pending.redirect_uri,
                pkce_verifier=pending.pkce_verifier,
                client_id=pending.client_id,
            )
            logger.warning("[OAuth] Token exchange succeeded for '%s'!", pending.server_name)
        except Exception as e:
            logger.warning("[OAuth] Token exchange FAILED for '%s': %s", pending.server_name, e, exc_info=True)
            return False

        # Store tokens
        self._token_store.save(pending.server_name, tokens, pending.auth_meta)

        # Try to connect the server with the new token (best-effort)
        client = self._clients.get(pending.server_name)
        if client:
            client.set_oauth_token(tokens.access_token)
            try:
                await client.close()
                await client.connect()
                if client.status == "connected":
                    logger.warning("[OAuth] MCP connection succeeded for '%s'", pending.server_name)
                else:
                    logger.warning("[OAuth] MCP connection status: %s (token stored OK)", client.status)
            except Exception as e:
                logger.warning("[OAuth] MCP reconnect failed for '%s': %s (token stored OK)", pending.server_name, e)

        # Token was obtained — that's a success regardless of MCP connection
        return True

    async def disconnect_auth(self, name: str) -> bool:
        """Remove stored tokens and disconnect a server."""
        self._token_store.delete(name)

        client = self._clients.get(name)
        if client:
            client.set_oauth_token(None)
            await client.close()
            client.status = "needs_auth"
            client.error = None

        return True
