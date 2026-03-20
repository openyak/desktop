"""Generic async CRUD repository helpers."""

from __future__ import annotations

from typing import Any, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import Base

T = TypeVar("T", bound=Base)


async def get_by_id(db: AsyncSession, model: type[T], id: str) -> T | None:
    """Get a record by primary key."""
    return await db.get(model, id)


async def get_all(
    db: AsyncSession,
    model: type[T],
    *,
    limit: int = 100,
    offset: int = 0,
    order_by: Any = None,
    filters: list[Any] | None = None,
) -> list[T]:
    """Get all records with optional filtering and pagination."""
    stmt = select(model)
    if filters:
        for f in filters:
            stmt = stmt.where(f)
    if order_by is not None:
        stmt = stmt.order_by(order_by)
    stmt = stmt.offset(offset).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def create(db: AsyncSession, instance: T) -> T:
    """Create a new record."""
    db.add(instance)
    await db.flush()
    await db.refresh(instance)
    return instance


async def delete_by_id(db: AsyncSession, model: type[T], id: str) -> bool:
    """Delete a record by primary key. Returns True if deleted."""
    instance = await get_by_id(db, model, id)
    if instance:
        await db.delete(instance)
        await db.flush()
        return True
    return False
