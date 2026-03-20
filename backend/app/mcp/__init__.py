"""MCP (Model Context Protocol) integration.

Connects to external MCP servers (local stdio or remote HTTP/SSE)
and exposes their tools as OpenYak ToolDefinitions.
"""

from app.mcp.manager import McpManager
from app.mcp.tool_wrapper import McpToolWrapper

__all__ = ["McpManager", "McpToolWrapper"]
