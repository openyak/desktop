"""Project model — represents a workspace/directory binding."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.utils.id import generate_ulid

if TYPE_CHECKING:
    from app.models.session import Session


class Project(Base, TimestampMixin):
    __tablename__ = "project"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_ulid)
    name: Mapped[str] = mapped_column(String, nullable=False)
    worktree: Mapped[str] = mapped_column(String, nullable=False)

    sessions: Mapped[list[Session]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
