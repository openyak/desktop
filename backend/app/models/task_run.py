"""TaskRun model — execution history for scheduled tasks."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin
from app.utils.id import generate_ulid


class TaskRun(Base, TimestampMixin):
    __tablename__ = "task_run"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_ulid)
    task_id: Mapped[str] = mapped_column(
        ForeignKey("scheduled_task.id", ondelete="CASCADE"), nullable=False, index=True
    )
    session_id: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    # "pending" | "running" | "success" | "error" | "skipped"
    error_message: Mapped[str | None] = mapped_column(String, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    triggered_by: Mapped[str] = mapped_column(String, nullable=False, default="schedule")
    # "schedule" | "manual" | "startup_catchup"
