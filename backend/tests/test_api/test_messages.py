"""Tests for message listing API endpoints."""

from __future__ import annotations

import pytest
from app.session.manager import create_message, create_part, create_session

pytestmark = pytest.mark.asyncio


class TestListMessages:
    async def test_empty_session(self, app_client, session_factory):
        async with session_factory() as db:
            async with db.begin():
                s = await create_session(db, title="Empty")
                sid = s.id
        resp = await app_client.get(f"/api/messages/{sid}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["messages"] == []

    async def test_with_parts(self, app_client, session_factory):
        async with session_factory() as db:
            async with db.begin():
                s = await create_session(db, title="Chat")
                sid = s.id
                msg = await create_message(db, session_id=sid, data={"role": "user"})
                await create_part(db, message_id=msg.id, session_id=sid, data={"type": "text", "text": "Hi"})
        resp = await app_client.get(f"/api/messages/{sid}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["messages"][0]["data"]["role"] == "user"
        assert len(data["messages"][0]["parts"]) == 1

    async def test_negative_offset_latest(self, app_client, session_factory):
        async with session_factory() as db:
            async with db.begin():
                s = await create_session(db, title="Many")
                sid = s.id
                for i in range(5):
                    await create_message(db, session_id=sid, data={"role": "user", "i": i})
        resp = await app_client.get(f"/api/messages/{sid}", params={"offset": -1, "limit": 2})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 5
        assert len(data["messages"]) == 2
        assert data["offset"] == 3

    async def test_explicit_offset(self, app_client, session_factory):
        async with session_factory() as db:
            async with db.begin():
                s = await create_session(db, title="Page")
                sid = s.id
                for i in range(3):
                    await create_message(db, session_id=sid, data={"role": "user"})
        resp = await app_client.get(f"/api/messages/{sid}", params={"offset": 0, "limit": 2})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 3
        assert data["offset"] == 0
        assert len(data["messages"]) == 2


class TestGetMessage:
    async def test_existing(self, app_client, session_factory):
        async with session_factory() as db:
            async with db.begin():
                s = await create_session(db, title="T")
                sid = s.id
                msg = await create_message(db, session_id=sid, data={"role": "assistant"})
                mid = msg.id
        resp = await app_client.get(f"/api/messages/{sid}/{mid}")
        assert resp.status_code == 200
        assert resp.json()["data"]["role"] == "assistant"

    async def test_not_found(self, app_client, session_factory):
        async with session_factory() as db:
            async with db.begin():
                s = await create_session(db, title="T")
                sid = s.id
        resp = await app_client.get(f"/api/messages/{sid}/nonexistent")
        assert resp.status_code == 404

    async def test_wrong_session(self, app_client, session_factory):
        async with session_factory() as db:
            async with db.begin():
                s1 = await create_session(db, title="S1")
                s2 = await create_session(db, title="S2")
                msg = await create_message(db, session_id=s1.id, data={"role": "user"})
        resp = await app_client.get(f"/api/messages/{s2.id}/{msg.id}")
        assert resp.status_code == 404
