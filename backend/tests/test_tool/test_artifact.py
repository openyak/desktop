"""Tests for app.tool.builtin.artifact — artifact create/update/rewrite."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.schemas.agent import AgentInfo
from app.tool.builtin.artifact import ArtifactTool
from app.tool.context import ToolContext


def _make_ctx() -> ToolContext:
    ctx = ToolContext(
        session_id="test-session",
        message_id="test-msg",
        agent=AgentInfo(name="test", description="", mode="primary"),
        call_id="test-call",
    )
    # ArtifactTool reads ctx._job.artifact_cache
    ctx._job = SimpleNamespace(artifact_cache={})
    return ctx


class TestArtifactTool:
    @pytest.fixture
    def tool(self):
        return ArtifactTool()

    @pytest.mark.asyncio
    async def test_create(self, tool: ArtifactTool):
        ctx = _make_ctx()
        result = await tool.execute({
            "command": "create",
            "identifier": "my-comp",
            "type": "react",
            "title": "My Component",
            "content": "<div>Hello</div>",
        }, ctx)
        assert result.success
        assert result.metadata["content"] == "<div>Hello</div>"
        assert result.metadata["type"] == "react"

    @pytest.mark.asyncio
    async def test_create_missing_fields(self, tool: ArtifactTool):
        ctx = _make_ctx()
        result = await tool.execute({
            "command": "create",
            "identifier": "my-comp",
            # missing type, title, content
        }, ctx)
        assert not result.success

    @pytest.mark.asyncio
    async def test_update_first_occurrence(self, tool: ArtifactTool):
        ctx = _make_ctx()
        await tool.execute({
            "command": "create",
            "identifier": "doc",
            "type": "code",
            "title": "Code",
            "content": "AAA BBB AAA",
        }, ctx)
        result = await tool.execute({
            "command": "update",
            "identifier": "doc",
            "old_str": "AAA",
            "new_str": "CCC",
        }, ctx)
        assert result.success
        assert result.metadata["content"] == "CCC BBB AAA"

    @pytest.mark.asyncio
    async def test_update_nonexistent_errors(self, tool: ArtifactTool):
        ctx = _make_ctx()
        result = await tool.execute({
            "command": "update",
            "identifier": "nope",
            "old_str": "x",
            "new_str": "y",
        }, ctx)
        assert not result.success
        assert "create" in result.error.lower()

    @pytest.mark.asyncio
    async def test_update_old_str_not_found(self, tool: ArtifactTool):
        ctx = _make_ctx()
        await tool.execute({
            "command": "create",
            "identifier": "doc",
            "type": "code",
            "title": "Code",
            "content": "hello world",
        }, ctx)
        result = await tool.execute({
            "command": "update",
            "identifier": "doc",
            "old_str": "MISSING",
            "new_str": "y",
        }, ctx)
        assert not result.success
        assert "not found" in result.error.lower()

    @pytest.mark.asyncio
    async def test_rewrite(self, tool: ArtifactTool):
        ctx = _make_ctx()
        await tool.execute({
            "command": "create",
            "identifier": "doc",
            "type": "markdown",
            "title": "Doc",
            "content": "old",
        }, ctx)
        result = await tool.execute({
            "command": "rewrite",
            "identifier": "doc",
            "content": "brand new content",
        }, ctx)
        assert result.success
        assert result.metadata["content"] == "brand new content"

    @pytest.mark.asyncio
    async def test_rewrite_nonexistent_errors(self, tool: ArtifactTool):
        ctx = _make_ctx()
        result = await tool.execute({
            "command": "rewrite",
            "identifier": "nope",
            "content": "x",
        }, ctx)
        assert not result.success

    @pytest.mark.asyncio
    async def test_unknown_command(self, tool: ArtifactTool):
        ctx = _make_ctx()
        result = await tool.execute({
            "command": "delete",
            "identifier": "doc",
        }, ctx)
        assert not result.success
        assert "Unknown" in result.error
