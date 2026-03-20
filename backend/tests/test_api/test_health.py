"""Tests for app.api.health — liveness and health endpoints."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from httpx import ASGITransport, AsyncClient
from fastapi import FastAPI

from app.api.health import router


def _create_test_app() -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    return app


class TestHealthEndpoints:
    @pytest.mark.asyncio
    async def test_livez_returns_ok(self):
        app = _create_test_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/livez")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    @pytest.mark.asyncio
    async def test_health_returns_providers(self):
        app = _create_test_app()

        # Mock provider registry
        async def mock_health():
            return {}

        app.state.provider_registry = SimpleNamespace(health=mock_health)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "providers" in data
