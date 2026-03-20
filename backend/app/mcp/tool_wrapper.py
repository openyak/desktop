"""MCP tool wrapper — adapts an MCP tool to the OpenYak ToolDefinition interface."""

from __future__ import annotations

import logging
from typing import Any, TYPE_CHECKING

from app.tool.base import ToolDefinition, ToolResult

if TYPE_CHECKING:
    from app.mcp.client import McpClient
    from app.tool.context import ToolContext
    from mcp.types import Tool as McpTool

logger = logging.getLogger(__name__)


class McpToolWrapper(ToolDefinition):
    """Wraps an MCP server tool as an OpenYak ToolDefinition.

    Tool ID: ``{server_name}_{tool_name}`` (sanitised).
    """

    def __init__(self, client: "McpClient", mcp_tool: "McpTool") -> None:
        self._client = client
        self._mcp_tool = mcp_tool
        self._tool_id = client.tool_id(mcp_tool.name)

    @property
    def id(self) -> str:
        return self._tool_id

    @property
    def description(self) -> str:
        desc = self._mcp_tool.description or f"MCP tool from {self._client.name}"
        return f"[MCP: {self._client.name}] {desc}"

    def parameters_schema(self) -> dict[str, Any]:
        schema = self._mcp_tool.inputSchema
        if isinstance(schema, dict):
            # Ensure it has type: object for OpenAI function calling
            result = dict(schema)
            result.setdefault("type", "object")
            result.setdefault("properties", {})
            return result
        return {"type": "object", "properties": {}}

    async def execute(self, args: dict[str, Any], ctx: "ToolContext") -> ToolResult:
        try:
            result = await self._client.call_tool(self._mcp_tool.name, args)
        except Exception as e:
            return ToolResult(error=f"MCP tool call failed: {e}")

        # Convert MCP result content to ToolResult
        text_parts: list[str] = []
        attachments: list[dict[str, Any]] = []

        for item in result.content:
            if item.type == "text":
                text_parts.append(item.text)
            elif item.type == "image":
                attachments.append({
                    "type": "file",
                    "mime_type": getattr(item, "mimeType", "image/png"),
                    "url": f"data:{getattr(item, 'mimeType', 'image/png')};base64,{item.data}",
                })
            elif item.type == "resource":
                resource = item.resource
                if hasattr(resource, "text") and resource.text:
                    text_parts.append(resource.text)
                elif hasattr(resource, "blob") and resource.blob:
                    attachments.append({
                        "type": "file",
                        "mime_type": getattr(resource, "mimeType", "application/octet-stream"),
                        "url": f"data:{getattr(resource, 'mimeType', 'application/octet-stream')};base64,{resource.blob}",
                    })

        output = "\n".join(text_parts)

        if result.isError:
            return ToolResult(error=output or "MCP tool returned an error")

        return ToolResult(
            output=output,
            title=f"{self._client.name}/{self._mcp_tool.name}",
            attachments=attachments,
        )
