"""Tests for auto title generation."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, PropertyMock

from app.schemas.agent import AgentInfo
from app.schemas.provider import ModelCapabilities, ModelInfo, StreamChunk
from app.session.title import generate_title

pytestmark = pytest.mark.asyncio


def _title_agent() -> AgentInfo:
    return AgentInfo(name="title", description="Title generator", mode="hidden", system_prompt="Generate a short title.", temperature=0.3)


def _model_info() -> ModelInfo:
    return ModelInfo(id="m1", name="M1", provider_id="p", capabilities=ModelCapabilities())


def _make_provider(title_text: str):
    p = MagicMock()

    async def _stream(*a, **kw):
        yield StreamChunk(type="text-delta", data={"text": title_text})

    p.stream_chat = MagicMock(side_effect=lambda *a, **kw: _stream(*a, **kw))
    return p


class TestGenerateTitle:
    async def test_normal(self):
        ar = MagicMock()
        ar.get.return_value = _title_agent()
        pr = MagicMock()
        pr.all_models.return_value = [_model_info()]
        pr.resolve_model.return_value = (_make_provider("Python Tutorial"), _model_info())

        title = await generate_title("Help me learn Python", provider_registry=pr, agent_registry=ar)
        assert title == "Python Tutorial"

    async def test_strips_quotes(self):
        ar = MagicMock()
        ar.get.return_value = _title_agent()
        pr = MagicMock()
        pr.all_models.return_value = [_model_info()]
        pr.resolve_model.return_value = (_make_provider('"My Title"'), _model_info())

        title = await generate_title("test", provider_registry=pr, agent_registry=ar)
        assert title == "My Title"

    async def test_truncates_long(self):
        ar = MagicMock()
        ar.get.return_value = _title_agent()
        pr = MagicMock()
        pr.all_models.return_value = [_model_info()]
        long_title = "A" * 200
        pr.resolve_model.return_value = (_make_provider(long_title), _model_info())

        title = await generate_title("test", provider_registry=pr, agent_registry=ar)
        assert len(title) <= 100

    async def test_no_title_agent(self):
        ar = MagicMock()
        ar.get.return_value = None
        pr = MagicMock()
        title = await generate_title("test", provider_registry=pr, agent_registry=ar)
        assert title is None

    async def test_no_models(self):
        ar = MagicMock()
        ar.get.return_value = _title_agent()
        pr = MagicMock()
        pr.all_models.return_value = []
        title = await generate_title("test", provider_registry=pr, agent_registry=ar)
        assert title is None

    async def test_resolve_fails(self):
        ar = MagicMock()
        ar.get.return_value = _title_agent()
        pr = MagicMock()
        pr.all_models.return_value = [_model_info()]
        pr.resolve_model.return_value = None
        title = await generate_title("test", provider_registry=pr, agent_registry=ar)
        assert title is None

    async def test_provider_error_returns_none(self):
        ar = MagicMock()
        ar.get.return_value = _title_agent()
        pr = MagicMock()
        pr.all_models.return_value = [_model_info()]

        bad_p = MagicMock()
        async def _fail(*a, **kw):
            raise RuntimeError("boom")
            yield  # noqa: unreachable — makes this an async generator
        bad_p.stream_chat = MagicMock(side_effect=lambda *a, **kw: _fail(*a, **kw))
        pr.resolve_model.return_value = (bad_p, _model_info())

        title = await generate_title("test", provider_registry=pr, agent_registry=ar)
        assert title is None
