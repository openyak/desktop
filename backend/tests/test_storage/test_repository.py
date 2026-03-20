"""Tests for app.storage.repository — generic async CRUD helpers."""

from __future__ import annotations

import pytest
import pytest_asyncio

from app.models.session import Session
from app.storage.repository import create, delete_by_id, get_all, get_by_id


class TestRepository:
    @pytest.mark.asyncio
    async def test_create_and_get_by_id(self, db):
        s = Session(title="Test Session")
        created = await create(db, s)
        assert created.id
        fetched = await get_by_id(db, Session, created.id)
        assert fetched is not None
        assert fetched.title == "Test Session"

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, db):
        result = await get_by_id(db, Session, "nonexistent-id")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_all_empty(self, db):
        result = await get_all(db, Session)
        assert result == []

    @pytest.mark.asyncio
    async def test_get_all_with_records(self, db):
        await create(db, Session(title="S1"))
        await create(db, Session(title="S2"))
        result = await get_all(db, Session)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_get_all_limit_and_offset(self, db):
        for i in range(5):
            await create(db, Session(title=f"S{i}"))
        result = await get_all(db, Session, limit=2, offset=2)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_get_all_with_filters(self, db):
        await create(db, Session(title="target"))
        await create(db, Session(title="other"))
        result = await get_all(db, Session, filters=[Session.title == "target"])
        assert len(result) == 1
        assert result[0].title == "target"

    @pytest.mark.asyncio
    async def test_get_all_order_by(self, db):
        await create(db, Session(title="B"))
        await create(db, Session(title="A"))
        result = await get_all(db, Session, order_by=Session.title)
        assert result[0].title == "A"
        assert result[1].title == "B"

    @pytest.mark.asyncio
    async def test_delete_existing(self, db):
        s = await create(db, Session(title="To Delete"))
        deleted = await delete_by_id(db, Session, s.id)
        assert deleted is True
        assert await get_by_id(db, Session, s.id) is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, db):
        deleted = await delete_by_id(db, Session, "no-such-id")
        assert deleted is False
