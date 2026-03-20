"""Health check and lifecycle endpoints."""

from __future__ import annotations

import logging
import os
import signal

from fastapi import APIRouter, Request

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/livez")
async def livez() -> dict:
    """Lightweight liveness probe. No external calls."""
    return {"status": "ok"}


@router.get("/health")
async def health(request: Request) -> dict:
    """Health check with provider status."""
    registry = getattr(request.app.state, "provider_registry", None)
    providers = {}
    if registry:
        providers = {
            pid: status.model_dump()
            for pid, status in (await registry.health()).items()
        }
    return {"status": "ok", "providers": providers}


@router.post("/shutdown")
async def shutdown() -> dict:
    """Graceful shutdown endpoint for desktop app.

    Sends SIGINT to self, which triggers FastAPI's lifespan shutdown
    (abort active jobs, dispose DB engine, etc.) before exiting.
    On Windows, uses CTRL_BREAK_EVENT as SIGINT equivalent.
    """
    logger.info("Shutdown requested via /shutdown endpoint")
    pid = os.getpid()
    if os.name == "nt":
        # Windows: os.kill with CTRL_BREAK_EVENT triggers KeyboardInterrupt
        os.kill(pid, signal.CTRL_BREAK_EVENT)
    else:
        os.kill(pid, signal.SIGINT)
    return {"status": "shutting_down"}
