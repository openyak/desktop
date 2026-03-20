"""Submit plan tool — present a structured plan for user review.

Follows the same blocking pattern as question.py: publishes an SSE event,
then blocks until the user accepts or requests revisions via POST /api/chat/respond.
On accept the tool returns metadata to switch agent to build mode.

Plans are persisted as markdown files in the app data directory (data/plans/).
"""

from __future__ import annotations

import json
import logging
import random
from pathlib import Path
from typing import Any

from app.tool.base import ToolDefinition, ToolResult
from app.tool.context import ToolContext

logger = logging.getLogger(__name__)

# Word lists for random plan file names (adjective-verb-noun, like Claude Code)
_ADJECTIVES = [
    "calm", "bold", "warm", "cool", "swift", "keen", "pale", "bright",
    "wild", "soft", "deep", "clear", "quiet", "gentle", "vivid", "subtle",
    "steady", "crisp", "light", "sharp", "smooth", "fresh", "silent", "rapid",
]
_VERBS = [
    "rising", "flowing", "drifting", "glowing", "spinning", "racing",
    "diving", "soaring", "dancing", "weaving", "blazing", "sailing",
    "chasing", "orbiting", "rolling", "winding", "climbing", "floating",
    "sparking", "humming", "fading", "rushing", "pulsing", "turning",
]
_NOUNS = [
    "falcon", "river", "ember", "crystal", "whisper", "thunder",
    "shadow", "breeze", "comet", "nebula", "meadow", "glacier",
    "phoenix", "quokka", "cedar", "prism", "beacon", "harbor",
    "canyon", "aurora", "pebble", "lantern", "sparrow", "summit",
]


def _random_plan_name() -> str:
    """Generate a random plan filename like 'calm-flowing-falcon'."""
    return f"{random.choice(_ADJECTIVES)}-{random.choice(_VERBS)}-{random.choice(_NOUNS)}"


def _write_plan_file(title: str, plan: str) -> str:
    """Write plan markdown to data/plans/ (app data dir) and return the file path."""
    plan_dir = Path("data/plans")
    plan_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{_random_plan_name()}.md"
    plan_path = plan_dir / filename
    # Avoid name collisions
    while plan_path.exists():
        filename = f"{_random_plan_name()}.md"
        plan_path = plan_dir / filename

    plan_path.write_text(f"# {title}\n\n{plan}", encoding="utf-8")
    return str(plan_path)


class SubmitPlanTool(ToolDefinition):
    """Submit a structured implementation plan for user review."""

    @property
    def id(self) -> str:
        return "submit_plan"

    @property
    def description(self) -> str:
        return (
            "Submit a structured implementation plan for user review. "
            "The plan will be displayed in a review panel where the user can "
            "accept it (switching to build mode for execution) or request revisions."
        )

    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Short title for the plan (e.g. 'Add dark mode toggle')",
                },
                "plan": {
                    "type": "string",
                    "description": (
                        "The full plan in markdown format. Include: "
                        "context/summary, numbered implementation steps with file paths, "
                        "and verification steps."
                    ),
                },
                "files_to_modify": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of file paths that will be created or modified",
                },
            },
            "required": ["title", "plan", "files_to_modify"],
        }

    async def execute(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        title = args["title"]
        plan = args["plan"]
        files = args.get("files_to_modify", [])

        # Persist plan to disk
        plan_path = _write_plan_file(title, plan)
        logger.info("Plan written to: %s", plan_path)

        # Common metadata included in all return paths for frontend card rendering
        plan_meta = {
            "title": title,
            "plan": plan,
            "plan_path": plan_path,
            "files_to_modify": files,
        }

        # Access the GenerationJob for wait_for_response
        job = getattr(ctx, "_job", None)

        # Publish plan-review event to SSE stream
        if ctx._publish_fn:
            ctx._publish_fn("plan-review", {
                "call_id": ctx.call_id,
                "title": title,
                "plan": plan,
                "plan_path": plan_path,
                "files_to_modify": files,
                "session_id": ctx.session_id,
            })

        # If no job context or not interactive — degrade gracefully
        if job is None or not job.interactive:
            return ToolResult(
                output=f"[No user connected] Plan submitted: {title}",
                title=f"Plan: {title}",
                metadata=plan_meta,
            )

        # Block until user responds via POST /api/chat/respond
        try:
            response = await job.wait_for_response(ctx.call_id, timeout=600.0)

            # Parse the response — expected: {"action": "accept"|"revise"|"stop", ...}
            if isinstance(response, str):
                try:
                    response = json.loads(response)
                except (json.JSONDecodeError, TypeError):
                    pass

            if isinstance(response, dict):
                action = response.get("action", "accept")

                if action == "accept":
                    mode = response.get("mode", "auto")
                    return ToolResult(
                        output=(
                            f"Plan accepted by user (mode: {mode}). "
                            f"Switch to build mode and implement the plan:\n\n{plan}"
                        ),
                        title=f"Plan accepted: {title}",
                        metadata={
                            **plan_meta,
                            "switch_agent": "build",
                            "plan_accepted": True,
                            "build_mode": mode,
                        },
                    )
                elif action == "stop":
                    # User wants to stop and review the plan at their leisure
                    return ToolResult(
                        output=(
                            "User chose to stop and review the plan independently. "
                            "The plan is saved for their review. Do not continue — "
                            "wait for the user's next message."
                        ),
                        title=f"Plan saved: {title}",
                        metadata={**plan_meta, "plan_stopped": True},
                    )
                else:  # revise
                    feedback = response.get("feedback", "")
                    return ToolResult(
                        output=(
                            f"User requested revisions to the plan.\n"
                            f"Feedback: {feedback}\n\n"
                            "Revise your plan based on this feedback and call submit_plan again."
                        ),
                        title="Plan revision requested",
                        metadata={**plan_meta, "plan_revised": True, "feedback": feedback},
                    )
            else:
                # Simple string response — treat as feedback
                return ToolResult(
                    output=f"User response: {response}\n\nRevise your plan and call submit_plan again.",
                    title="Plan response received",
                    metadata=plan_meta,
                )

        except TimeoutError:
            return ToolResult(
                output="(user did not respond within 10 minutes)",
                error="Plan review timed out — no response from user",
                metadata=plan_meta,
            )
