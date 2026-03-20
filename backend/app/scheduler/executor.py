"""Scheduled task executor — creates a headless agent session for a task."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.scheduled_task import ScheduledTask
from app.models.task_run import TaskRun
from app.schemas.chat import PromptRequest
from app.session.processor import run_generation
from app.streaming.manager import GenerationJob
from app.utils.id import generate_ulid

logger = logging.getLogger(__name__)


async def execute_scheduled_task(
    task_id: str,
    *,
    session_factory: async_sessionmaker[AsyncSession],
    app_state: Any,
    triggered_by: str = "schedule",
) -> str | None:
    """Execute a scheduled task by creating a headless agent session.

    Returns the session_id on success, or None if the task was not found/disabled.
    """
    # 1. Load task
    async with session_factory() as db:
        async with db.begin():
            task = (
                await db.execute(
                    select(ScheduledTask).where(ScheduledTask.id == task_id)
                )
            ).scalar_one_or_none()
            if task is None:
                logger.warning("Scheduled task %s not found", task_id)
                return None
            if not task.enabled and triggered_by != "manual":
                logger.debug("Scheduled task %s is disabled, skipping", task_id)
                return None
            # Snapshot task fields while inside the session
            task_name = task.name
            task_prompt = task.prompt
            task_agent = task.agent
            task_model = task.model
            task_workspace = task.workspace
            task_timeout = task.timeout_seconds or 1800

    # 1b. If no model specified, pick the best available (prefer subscription/paid)
    if not task_model:
        task_model = _resolve_default_model(app_state)

    # 2. Create IDs
    session_id = generate_ulid()
    run_id = generate_ulid()
    now = datetime.now(timezone.utc)

    # 3. Create TaskRun record
    async with session_factory() as db:
        async with db.begin():
            run = TaskRun(
                id=run_id,
                task_id=task_id,
                session_id=session_id,
                status="running",
                started_at=now,
                triggered_by=triggered_by,
            )
            db.add(run)

            # Update task status
            task_obj = (
                await db.execute(
                    select(ScheduledTask).where(ScheduledTask.id == task_id)
                )
            ).scalar_one_or_none()
            if task_obj:
                task_obj.last_run_status = "running"
                task_obj.last_session_id = session_id

    # 4. Create headless GenerationJob
    stream_id = generate_ulid()
    job = GenerationJob(stream_id=stream_id, session_id=session_id)
    # interactive=False → auto-approve permissions (already default in GenerationJob)

    # 5. Build PromptRequest
    request = PromptRequest(
        session_id=session_id,
        text=task_prompt,
        model=task_model,
        agent=task_agent,
        workspace=task_workspace,
    )

    # 6. Run generation (with timeout protection)
    status = "success"
    error_msg = None
    try:
        await asyncio.wait_for(
            run_generation(
                job,
                request,
                session_factory=session_factory,
                provider_registry=app_state.provider_registry,
                agent_registry=app_state.agent_registry,
                tool_registry=app_state.tool_registry,
                index_manager=getattr(app_state, "index_manager", None),
            ),
            timeout=task_timeout,
        )
    except asyncio.TimeoutError:
        status = "timeout"
        error_msg = f"Execution exceeded {task_timeout}s timeout"
        logger.warning("Scheduled task %s (%s) timed out after %ds", task_id, task_name, task_timeout)
    except Exception as e:
        status = "error"
        error_msg = str(e)
        logger.error("Scheduled task %s (%s) failed: %s", task_id, task_name, e)

    # 7. Update run record and task stats
    finished_at = datetime.now(timezone.utc)
    async with session_factory() as db:
        async with db.begin():
            run_obj = (
                await db.execute(select(TaskRun).where(TaskRun.id == run_id))
            ).scalar_one_or_none()
            if run_obj:
                run_obj.status = status
                run_obj.error_message = error_msg
                run_obj.finished_at = finished_at

            task_obj = (
                await db.execute(
                    select(ScheduledTask).where(ScheduledTask.id == task_id)
                )
            ).scalar_one_or_none()
            if task_obj:
                task_obj.last_run_at = finished_at
                task_obj.last_run_status = status
                task_obj.run_count = (task_obj.run_count or 0) + 1

    # 8. Set session title
    try:
        from app.session.manager import update_session_title

        async with session_factory() as db:
            async with db.begin():
                await update_session_title(
                    db,
                    session_id,
                    f"[Scheduled] {task_name} — {now.strftime('%m/%d %H:%M')}",
                )
    except Exception as e:
        logger.debug("Could not set session title for scheduled task: %s", e)

    logger.info(
        "Scheduled task %s (%s) finished: %s [triggered_by=%s]",
        task_id, task_name, status, triggered_by,
    )
    return session_id


def _resolve_default_model(app_state: Any) -> str | None:
    """Pick the best default model for scheduled tasks.

    Priority: subscription models > paid OpenRouter models > free models.
    This ensures scheduled tasks use the user's best available model,
    not the free fallback which may have rate limits.
    """
    registry = getattr(app_state, "provider_registry", None)
    if registry is None:
        return None

    all_models = registry.all_models()
    if not all_models:
        return None

    # 1. Prefer subscription models (openai-subscription, etc.)
    subscription = [m for m in all_models if m.provider_id == "openai-subscription"]
    if subscription:
        return subscription[0].id

    # 2. Prefer paid OpenRouter models
    paid = [m for m in all_models if m.pricing.prompt > 0 or m.pricing.completion > 0]
    if paid:
        return paid[0].id

    # 3. Fall back to first available model
    return all_models[0].id
