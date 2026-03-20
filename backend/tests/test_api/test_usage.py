"""Tests for usage statistics API endpoint."""

from __future__ import annotations

import pytest
from app.session.manager import create_message, create_session

pytestmark = pytest.mark.asyncio


class TestUsageStats:
    async def test_empty_database(self, app_client):
        resp = await app_client.get("/api/usage")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_cost"] == 0.0
        assert data["total_sessions"] == 0
        assert data["total_messages"] == 0

    async def test_with_data(self, app_client, session_factory):
        async with session_factory() as db:
            async with db.begin():
                s = await create_session(db, title="Usage")
                await create_message(db, session_id=s.id, data={
                    "role": "assistant", "model_id": "test", "provider_id": "p",
                    "cost": 0.001,
                    "tokens": {"input": 100, "output": 50, "reasoning": 0, "cache_read": 0, "cache_write": 0},
                })
        resp = await app_client.get("/api/usage")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_cost"] > 0
        assert data["total_messages"] == 1
        assert data["total_tokens"]["input"] == 100

    async def test_custom_days(self, app_client):
        resp = await app_client.get("/api/usage", params={"days": 7})
        assert resp.status_code == 200

    async def test_by_model(self, app_client, session_factory):
        async with session_factory() as db:
            async with db.begin():
                s = await create_session(db, title="Model")
                await create_message(db, session_id=s.id, data={
                    "role": "assistant", "model_id": "gpt-4", "provider_id": "or",
                    "cost": 0.01,
                    "tokens": {"input": 500, "output": 200, "reasoning": 0, "cache_read": 0, "cache_write": 0},
                })
        resp = await app_client.get("/api/usage")
        data = resp.json()
        assert len(data["by_model"]) == 1
        assert data["by_model"][0]["model_id"] == "gpt-4"
