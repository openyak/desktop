"""MCP client — connects to a single MCP server and proxies tool calls."""

from __future__ import annotations

import logging
import re
from contextlib import AsyncExitStack
from typing import Any

import anyio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.sse import sse_client
from mcp.client.streamable_http import streamablehttp_client
from mcp.types import CallToolResult, TextContent, Tool as McpTool

logger = logging.getLogger(__name__)

# Sanitise names to only contain alphanumeric, underscore, hyphen
_SANITISE_RE = re.compile(r"[^a-zA-Z0-9_-]")


def sanitise_name(name: str) -> str:
    return _SANITISE_RE.sub("_", name)


class McpClient:
    """Wrapper around a single MCP server connection."""

    def __init__(self, name: str, config: dict[str, Any]) -> None:
        self.name = name
        self.config = config
        self._session: ClientSession | None = None
        self._exit_stack: AsyncExitStack | None = None
        self._tools: list[McpTool] = []
        self.status: str = "disconnected"  # connected | disconnected | failed | needs_auth
        self.error: str | None = None
        self._oauth_token: str | None = None  # injected OAuth access token

    @property
    def server_type(self) -> str:
        return self.config.get("type", "local")

    @property
    def timeout(self) -> int:
        return self.config.get("timeout", 30)

    async def connect(self) -> None:
        """Connect to the MCP server and discover tools."""
        try:
            if self.server_type == "local":
                self._exit_stack = AsyncExitStack()
                await self._exit_stack.__aenter__()
                await self._connect_stdio()
            else:
                await self._connect_remote()

            # Discover tools
            result = await self._session.list_tools()  # type: ignore[union-attr]
            self._tools = result.tools
            self.status = "connected"
            self.error = None
            logger.info(
                "MCP server '%s' connected — %d tools available",
                self.name,
                len(self._tools),
            )
        except Exception as e:
            self.status = "failed"
            self.error = str(e)
            logger.warning("Failed to connect to MCP server '%s': %s", self.name, e)
            await self._cleanup()

    async def _connect_stdio(self) -> None:
        """Connect via stdio transport (local subprocess)."""
        command = self.config.get("command", [])
        if not command:
            raise ValueError(f"MCP server '{self.name}': 'command' is required for local type")

        env = self.config.get("environment")
        server_params = StdioServerParameters(
            command=command[0],
            args=command[1:] if len(command) > 1 else [],
            env=env,
        )

        read_stream, write_stream = await self._exit_stack.enter_async_context(  # type: ignore[union-attr]
            stdio_client(server_params)
        )
        self._session = await self._exit_stack.enter_async_context(  # type: ignore[union-attr]
            ClientSession(read_stream, write_stream)
        )
        await self._session.initialize()

    async def _connect_remote(self) -> None:
        """Connect via HTTP/SSE transport (remote server)."""
        url = self.config.get("url")
        if not url:
            raise ValueError(f"MCP server '{self.name}': 'url' is required for remote type")

        headers = dict(self.config.get("headers", {}))

        # Inject OAuth token if available
        if self._oauth_token:
            headers["Authorization"] = f"Bearer {self._oauth_token}"

        # Try streamable HTTP first, fall back to SSE
        try:
            await self._try_transport(
                lambda stack: self._enter_streamable_http(stack, url, headers),
            )
            return
        except Exception as e:
            logger.warning(
                "MCP server '%s': streamable HTTP failed: %s", self.name, e,
            )

        # Fall back to SSE
        try:
            await self._try_transport(
                lambda stack: self._enter_sse(stack, url, headers),
            )
        except Exception as e:
            logger.warning(
                "MCP server '%s': SSE also failed: %s", self.name, e,
            )
            raise

    async def _try_transport(self, enter_fn: Any) -> None:
        """Attempt a transport connection with its own isolated exit stack.

        On success, promotes the stack to self._exit_stack.
        On failure, cleans up the stack defensively and re-raises.

        NOTE: We must NOT wrap the context-manager entry in
        ``anyio.fail_after`` because the MCP SDK's transports create
        internal task-groups / cancel-scopes that must be entered and
        exited in the same task context.  ``fail_after`` creates a
        cancel scope that conflicts with this requirement.
        """
        stack = AsyncExitStack()
        await stack.__aenter__()
        try:
            await enter_fn(stack)
        except BaseException as e:
            await self._close_stack(stack)
            if isinstance(e, Exception):
                raise
            raise RuntimeError(f"MCP transport failed: {e}") from e
        # Success — adopt the stack
        self._exit_stack = stack

    async def _enter_streamable_http(
        self, stack: AsyncExitStack, url: str, headers: dict[str, str],
    ) -> None:
        read_stream, write_stream, _ = await stack.enter_async_context(
            streamablehttp_client(url, headers=headers)
        )
        self._session = await stack.enter_async_context(
            ClientSession(read_stream, write_stream)
        )
        await self._session.initialize()

    async def _enter_sse(
        self, stack: AsyncExitStack, url: str, headers: dict[str, str],
    ) -> None:
        read_stream, write_stream = await stack.enter_async_context(
            sse_client(url, headers=headers)
        )
        self._session = await stack.enter_async_context(
            ClientSession(read_stream, write_stream)
        )
        await self._session.initialize()

    async def close(self) -> None:
        """Disconnect from the MCP server."""
        await self._cleanup()
        self.status = "disconnected"
        self._tools = []

    @staticmethod
    async def _close_stack(stack: AsyncExitStack) -> None:
        """Close an exit stack, swallowing errors from cross-task cancel scope teardown."""
        try:
            await stack.aclose()
        except BaseException:
            # CancelledError (BaseException in Python 3.9+) and RuntimeError from
            # cross-task cancel scope teardown must both be suppressed here.
            logger.debug("Error closing MCP exit stack (suppressed)", exc_info=True)

    async def _cleanup(self) -> None:
        if self._exit_stack:
            await self._close_stack(self._exit_stack)
            self._exit_stack = None
        self._session = None

    def set_oauth_token(self, token: str | None) -> None:
        """Set or clear the OAuth access token for this client."""
        self._oauth_token = token

    def list_tools(self) -> list[McpTool]:
        """Return the list of tools discovered from this server."""
        return list(self._tools)

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> CallToolResult:
        """Call a tool on the MCP server."""
        if self._session is None:
            raise RuntimeError(f"MCP server '{self.name}' is not connected")
        return await self._session.call_tool(tool_name, arguments)

    def tool_id(self, tool_name: str) -> str:
        """Generate a unique tool ID for a tool from this server."""
        return f"{sanitise_name(self.name)}_{sanitise_name(tool_name)}"
