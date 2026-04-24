"""Usage statistics endpoints."""

from __future__ import annotations

import statistics
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import DateTime, bindparam, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.models.message import Message
from app.models.session import Session

router = APIRouter()


# --- Response schemas ---


class TokenBreakdown(BaseModel):
    """Canonical token semantics.

    input: prompt tokens excluding cache hits
    output: non-reasoning completion tokens
    reasoning: reasoning completion tokens
    cache_read: prompt tokens read from cache
    cache_write: prompt tokens written to cache
    """

    input: int = 0
    output: int = 0
    reasoning: int = 0
    cache_read: int = 0
    cache_write: int = 0


class ModelUsage(BaseModel):
    model_id: str
    provider_id: str
    total_cost: float
    total_tokens: TokenBreakdown
    message_count: int


class SessionUsage(BaseModel):
    session_id: str
    title: str
    total_cost: float
    total_tokens: int
    message_count: int
    time_created: datetime


class DailyUsage(BaseModel):
    date: str
    cost: float
    tokens: int
    messages: int


class ResponseTimeStats(BaseModel):
    avg: float = 0.0
    median: float = 0.0
    p95: float = 0.0
    min: float = 0.0
    max: float = 0.0
    count: int = 0


class UsageStats(BaseModel):
    total_cost: float = 0.0
    total_tokens: TokenBreakdown = TokenBreakdown()
    total_sessions: int = 0
    total_messages: int = 0
    avg_tokens_per_session: float = 0.0
    avg_response_time: float = 0.0
    by_model: list[ModelUsage] = []
    by_session: list[SessionUsage] = []
    daily: list[DailyUsage] = []
    response_time: ResponseTimeStats = ResponseTimeStats()


# --- Endpoint ---


@router.get("/usage", response_model=UsageStats)
async def get_usage_stats(
    db: AsyncSession = Depends(get_db),
    days: int = Query(default=30, ge=1, le=365),
) -> UsageStats:
    """Aggregate usage statistics from message data."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    # --- Total cost and tokens from assistant messages ---
    totals_stmt = (
        select(
            func.count(Message.id).label("msg_count"),
            func.coalesce(
                func.sum(func.json_extract(Message.data, "$.cost")), 0
            ).label("total_cost"),
            func.coalesce(
                func.sum(func.json_extract(Message.data, "$.tokens.input")), 0
            ).label("total_input"),
            func.coalesce(
                func.sum(func.json_extract(Message.data, "$.tokens.output")), 0
            ).label("total_output"),
            func.coalesce(
                func.sum(func.json_extract(Message.data, "$.tokens.reasoning")), 0
            ).label("total_reasoning"),
            func.coalesce(
                func.sum(func.json_extract(Message.data, "$.tokens.cache_read")), 0
            ).label("total_cache_read"),
            func.coalesce(
                func.sum(func.json_extract(Message.data, "$.tokens.cache_write")), 0
            ).label("total_cache_write"),
        )
        .where(
            func.json_extract(Message.data, "$.role") == "assistant",
            Message.time_created >= cutoff,
        )
    )
    totals_row = (await db.execute(totals_stmt)).one()

    total_tokens = TokenBreakdown(
        input=int(totals_row.total_input),
        output=int(totals_row.total_output),
        reasoning=int(totals_row.total_reasoning),
        cache_read=int(totals_row.total_cache_read),
        cache_write=int(totals_row.total_cache_write),
    )
    total_cost = float(totals_row.total_cost)
    total_messages = int(totals_row.msg_count)

    # --- Total sessions (non-subtask only) ---
    session_count_stmt = (
        select(func.count(Session.id))
        .where(
            Session.parent_id.is_(None),
            Session.time_archived.is_(None),
            Session.time_created >= cutoff,
        )
    )
    total_sessions = (await db.execute(session_count_stmt)).scalar() or 0

    all_tokens = total_tokens.input + total_tokens.output + total_tokens.reasoning
    avg_tokens_per_session = all_tokens / total_sessions if total_sessions > 0 else 0.0

    # --- Per-model breakdown ---
    model_stmt = (
        select(
            func.json_extract(Message.data, "$.model_id").label("model_id"),
            func.json_extract(Message.data, "$.provider_id").label("provider_id"),
            func.count(Message.id).label("message_count"),
            func.coalesce(
                func.sum(func.json_extract(Message.data, "$.cost")), 0
            ).label("total_cost"),
            func.coalesce(
                func.sum(func.json_extract(Message.data, "$.tokens.input")), 0
            ).label("total_input"),
            func.coalesce(
                func.sum(func.json_extract(Message.data, "$.tokens.output")), 0
            ).label("total_output"),
            func.coalesce(
                func.sum(func.json_extract(Message.data, "$.tokens.reasoning")), 0
            ).label("total_reasoning"),
            func.coalesce(
                func.sum(func.json_extract(Message.data, "$.tokens.cache_read")), 0
            ).label("total_cache_read"),
            func.coalesce(
                func.sum(func.json_extract(Message.data, "$.tokens.cache_write")), 0
            ).label("total_cache_write"),
        )
        .where(
            func.json_extract(Message.data, "$.role") == "assistant",
            func.json_extract(Message.data, "$.model_id").isnot(None),
            Message.time_created >= cutoff,
        )
        .group_by(
            func.json_extract(Message.data, "$.model_id"),
            func.json_extract(Message.data, "$.provider_id"),
        )
        .having(
            # Filter out models with zero total tokens (unused models)
            (func.coalesce(func.sum(func.json_extract(Message.data, "$.tokens.input")), 0)
             + func.coalesce(func.sum(func.json_extract(Message.data, "$.tokens.output")), 0)
             + func.coalesce(func.sum(func.json_extract(Message.data, "$.tokens.reasoning")), 0)) > 0
        )
        .order_by(text("total_cost DESC"))
        .limit(20)
    )
    model_rows = (await db.execute(model_stmt)).all()
    by_model = [
        ModelUsage(
            model_id=row.model_id or "unknown",
            provider_id=row.provider_id or "unknown",
            total_cost=float(row.total_cost),
            total_tokens=TokenBreakdown(
                input=int(row.total_input),
                output=int(row.total_output),
                reasoning=int(row.total_reasoning),
                cache_read=int(row.total_cache_read),
                cache_write=int(row.total_cache_write),
            ),
            message_count=int(row.message_count),
        )
        for row in model_rows
    ]

    # --- Per-session breakdown (top 10 by cost) ---
    session_stmt = (
        select(
            Message.session_id,
            Session.title,
            Session.time_created.label("session_created"),
            func.count(Message.id).label("message_count"),
            func.coalesce(
                func.sum(func.json_extract(Message.data, "$.cost")), 0
            ).label("total_cost"),
            func.coalesce(
                func.sum(func.json_extract(Message.data, "$.tokens.input")), 0
            ).label("total_input"),
            func.coalesce(
                func.sum(func.json_extract(Message.data, "$.tokens.output")), 0
            ).label("total_output"),
            func.coalesce(
                func.sum(func.json_extract(Message.data, "$.tokens.reasoning")), 0
            ).label("total_reasoning"),
        )
        .join(Session, Message.session_id == Session.id)
        .where(
            func.json_extract(Message.data, "$.role") == "assistant",
            Session.parent_id.is_(None),
            Message.time_created >= cutoff,
        )
        .group_by(Message.session_id)
        .order_by(text("total_cost DESC"))
        .limit(10)
    )
    session_rows = (await db.execute(session_stmt)).all()
    by_session = [
        SessionUsage(
            session_id=row.session_id,
            title=row.title or "Untitled",
            total_cost=float(row.total_cost),
            total_tokens=int(row.total_input) + int(row.total_output) + int(row.total_reasoning),
            message_count=int(row.message_count),
            time_created=row.session_created,
        )
        for row in session_rows
    ]

    # --- Daily usage trend ---
    daily_stmt = (
        select(
            func.date(Message.time_created).label("date"),
            func.count(Message.id).label("messages"),
            func.coalesce(
                func.sum(func.json_extract(Message.data, "$.cost")), 0
            ).label("cost"),
            func.coalesce(
                func.sum(func.json_extract(Message.data, "$.tokens.input")), 0
            ).label("tokens_in"),
            func.coalesce(
                func.sum(func.json_extract(Message.data, "$.tokens.output")), 0
            ).label("tokens_out"),
            func.coalesce(
                func.sum(func.json_extract(Message.data, "$.tokens.reasoning")), 0
            ).label("tokens_reasoning"),
        )
        .where(
            func.json_extract(Message.data, "$.role") == "assistant",
            Message.time_created >= cutoff,
        )
        .group_by(func.date(Message.time_created))
        .order_by(func.date(Message.time_created))
    )
    daily_rows = (await db.execute(daily_stmt)).all()
    daily = [
        DailyUsage(
            date=str(row.date),
            cost=float(row.cost),
            tokens=int(row.tokens_in) + int(row.tokens_out) + int(row.tokens_reasoning),
            messages=int(row.messages),
        )
        for row in daily_rows
    ]

    # --- Response time calculation ---
    # Use SQL window function (LAG) to compute user→assistant deltas in DB,
    # avoiding loading all message pairs into Python.
    rt_stmt = text("""
        SELECT delta_seconds FROM (
            SELECT
                (julianday(time_created) - julianday(
                    LAG(time_created) OVER (PARTITION BY session_id ORDER BY time_created)
                )) * 86400.0 as delta_seconds,
                role,
                LAG(role) OVER (PARTITION BY session_id ORDER BY time_created) as prev_role
            FROM (
                SELECT m.session_id, json_extract(m.data, '$.role') as role, m.time_created
                FROM message m
                JOIN session s ON m.session_id = s.id
                WHERE s.parent_id IS NULL
                  AND m.time_created >= :cutoff
                  AND json_extract(m.data, '$.role') IN ('user', 'assistant')
            )
        )
        WHERE role = 'assistant' AND prev_role = 'user'
          AND delta_seconds > 0 AND delta_seconds < 600
    """).bindparams(bindparam("cutoff", type_=DateTime))
    rt_rows = (await db.execute(rt_stmt, {"cutoff": cutoff})).all()
    response_times: list[float] = [float(row.delta_seconds) for row in rt_rows]

    rt_stats = ResponseTimeStats()
    if response_times:
        sorted_rt = sorted(response_times)
        p95_idx = int(len(sorted_rt) * 0.95)
        rt_stats = ResponseTimeStats(
            avg=round(statistics.mean(sorted_rt), 2),
            median=round(statistics.median(sorted_rt), 2),
            p95=round(sorted_rt[min(p95_idx, len(sorted_rt) - 1)], 2),
            min=round(sorted_rt[0], 2),
            max=round(sorted_rt[-1], 2),
            count=len(sorted_rt),
        )

    return UsageStats(
        total_cost=round(total_cost, 6),
        total_tokens=total_tokens,
        total_sessions=total_sessions,
        total_messages=total_messages,
        avg_tokens_per_session=round(avg_tokens_per_session, 1),
        avg_response_time=rt_stats.avg,
        by_model=by_model,
        by_session=by_session,
        daily=daily,
        response_time=rt_stats,
    )
