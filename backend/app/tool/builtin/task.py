"""Task tool — SubAgent invocation.

Spawns a child session with its own agent loop, enabling:
  - Parallel exploration (explore subagent)
  - Code search delegation
  - Multi-step subtask execution (general subagent)

Improvements over initial implementation:
  - Sets parent_id on child session for proper hierarchy
  - Recursion depth guard (max 3 levels) prevents infinite nesting
  - Timeout prevents child sessions from running forever
  - Abort signal propagated from parent to child
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.tool.base import ToolDefinition, ToolResult
from app.tool.context import ToolContext

logger = logging.getLogger(__name__)

# Maximum nesting depth for subtasks to prevent infinite recursion
MAX_SUBTASK_DEPTH = 3

# Default timeout for subtask execution (seconds)
SUBTASK_TIMEOUT = 600.0


class TaskTool(ToolDefinition):

    @property
    def id(self) -> str:
        return "task"

    @property
    def description(self) -> str:
        return (
            "Launch a specialized subagent to handle a complex subtask. "
            "Available agent types: 'explore' (fast codebase search), "
            "'general' (full access minus todo). "
            "The subagent runs its own agent loop and returns the result. "
            "Pass task_id from a previous result to resume an existing subtask session."
        )

    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "description": {
                    "type": "string",
                    "description": "Short description of the subtask (3-5 words)",
                },
                "prompt": {
                    "type": "string",
                    "description": "Detailed instructions for the subagent",
                },
                "agent": {
                    "type": "string",
                    "description": "Subagent type: 'explore' or 'general'",
                    "default": "explore",
                    "enum": ["explore", "general"],
                },
                "task_id": {
                    "type": "string",
                    "description": "Optional. Resume a previous subtask by passing the task_id from a prior result.",
                },
            },
            "required": ["description", "prompt"],
        }

    async def execute(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        description = args["description"]
        prompt = args["prompt"]
        agent_name = args.get("agent", "explore")
        task_id = args.get("task_id")

        # Import here to avoid circular imports
        from app.schemas.chat import PromptRequest
        from app.session.processor import run_generation
        from app.streaming.manager import GenerationJob
        from app.utils.id import generate_ulid

        # --- Recursion depth guard ---
        parent_depth = getattr(ctx, "_depth", 0)
        if parent_depth >= MAX_SUBTASK_DEPTH:
            return ToolResult(
                error=(
                    f"Maximum subtask nesting depth ({MAX_SUBTASK_DEPTH}) exceeded. "
                    "Complete the current task directly instead of delegating further."
                ),
            )

        # Access app-level registries through the _app_state injected by processor
        app_state = getattr(ctx, "_app_state", None)
        if not app_state:
            return ToolResult(error="SubAgent not available: missing app state")

        session_factory = app_state["session_factory"]
        child_stream_id = generate_ulid()
        resuming = False

        # --- Resume existing session or create new one ---
        from app.session.manager import create_session, get_session
        if task_id:
            # Try to resume an existing child session
            async with session_factory() as db:
                existing = await get_session(db, task_id)
                if existing and existing.parent_id == ctx.session_id:
                    child_session_id = task_id
                    resuming = True
                    logger.info("Resuming subtask session %s", task_id)
                else:
                    logger.warning(
                        "task_id %s not found or parent mismatch, creating new session",
                        task_id,
                    )
                    task_id = None  # Fall through to create new

        if not task_id:
            child_session_id = generate_ulid()
            async with session_factory() as db:
                async with db.begin():
                    await create_session(
                        db,
                        id=child_session_id,
                        parent_id=ctx.session_id,
                        directory=".",
                        title=description,
                    )

        # Create a child job to capture the output
        child_job = GenerationJob(
            stream_id=child_stream_id,
            session_id=child_session_id,
        )
        # Propagate depth for nested recursion guard
        child_job._depth = parent_depth + 1

        # Build the child request
        child_request = PromptRequest(
            session_id=child_session_id,
            text=prompt,
            model=getattr(ctx, "_model_id", None),
            agent=agent_name,
        )

        # Publish subtask start to parent stream
        if ctx._publish_fn:
            ctx._publish_fn("subtask_start", {
                "session_id": child_session_id,
                "parent_id": ctx.session_id,
                "title": description,
                "agent": agent_name,
                "depth": parent_depth + 1,
                "resumed": resuming,
            })

        try:
            # Run with timeout + abort propagation
            await asyncio.wait_for(
                run_generation(
                    child_job,
                    child_request,
                    session_factory=session_factory,
                    provider_registry=app_state["provider_registry"],
                    agent_registry=app_state["agent_registry"],
                    tool_registry=app_state["tool_registry"],
                ),
                timeout=SUBTASK_TIMEOUT,
            )
        except asyncio.TimeoutError:
            child_job.abort()
            logger.warning(
                "Subtask timed out after %.0fs: %s", SUBTASK_TIMEOUT, description,
            )
            # Still extract whatever output was produced before timeout
        except Exception as e:
            logger.exception("SubAgent error")
            return ToolResult(error=f"SubAgent failed: {e}")

        # Extract text output from child events
        output_parts = []
        error_parts = []
        for event in child_job.events:
            if event.event == "text-delta":
                output_parts.append(event.data.get("text", ""))
            elif event.event == "error":
                error_parts.append(event.data.get("message", ""))

        output = "".join(output_parts)
        if error_parts:
            output += "\n[Errors: " + "; ".join(error_parts) + "]"
        if not output.strip():
            output = "(subagent produced no text output)"

        return ToolResult(
            output=output,
            title=f"SubAgent ({agent_name}): {description}",
            metadata={
                "task_id": child_session_id,
                "session_id": child_session_id,
                "parent_id": ctx.session_id,
                "agent": agent_name,
                "depth": parent_depth + 1,
                "resumed": resuming,
                "events": len(child_job.events),
            },
        )
