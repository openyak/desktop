"""Tests for app.mcp.tool_wrapper — MCP tool schema normalization."""

from __future__ import annotations

import pytest

pytest.importorskip("mcp")

from types import SimpleNamespace

from app.mcp.tool_wrapper import McpToolWrapper


def _make_wrapper(input_schema: dict | None = None, description: str = "A tool") -> McpToolWrapper:
    client = SimpleNamespace(name="slack", tool_id=lambda name: f"slack_{name}")
    mcp_tool = SimpleNamespace(
        name="send_message",
        description=description,
        inputSchema=input_schema or {"type": "object", "properties": {"text": {"type": "string"}}},
    )
    return McpToolWrapper(client, mcp_tool)


class TestMcpToolWrapperSchema:
    def test_ensures_type_object(self):
        wrapper = _make_wrapper({"properties": {"x": {"type": "string"}}})
        schema = wrapper.parameters_schema()
        assert schema["type"] == "object"

    def test_ensures_properties_dict(self):
        wrapper = _make_wrapper({"type": "object"})
        schema = wrapper.parameters_schema()
        assert schema["properties"] == {}

    def test_passthrough_valid_schema(self):
        original = {"type": "object", "properties": {"x": {"type": "string"}}, "required": ["x"]}
        wrapper = _make_wrapper(original)
        schema = wrapper.parameters_schema()
        assert schema["required"] == ["x"]
        assert "x" in schema["properties"]


class TestMcpToolWrapperDescription:
    def test_prefixes_server_name(self):
        wrapper = _make_wrapper(description="Send a message")
        assert wrapper.description.startswith("[MCP: slack]")
        assert "Send a message" in wrapper.description
