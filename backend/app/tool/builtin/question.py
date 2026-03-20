"""Question tool — ask the user a question and wait for response.

Actually blocks until the user responds via POST /api/chat/respond,
matching OpenCode's behavior. Degrades gracefully in headless/test mode.
"""

from __future__ import annotations

import logging
from typing import Any

from app.tool.base import ToolDefinition, ToolResult
from app.tool.context import ToolContext

logger = logging.getLogger(__name__)


class QuestionTool(ToolDefinition):

    @property
    def id(self) -> str:
        return "question"

    @property
    def description(self) -> str:
        return (
            "Ask the user a question and wait for their response. "
            "Use this when you need clarification or user input to proceed."
        )

    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "The question to ask the user",
                },
                "options": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional list of choices for the user",
                },
            },
            "required": ["question"],
        }

    async def execute(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        question = args["question"]
        options = args.get("options", [])

        # Access the GenerationJob for wait_for_response
        job = getattr(ctx, "_job", None)

        # Publish question event to SSE stream
        if ctx._publish_fn:
            ctx._publish_fn("question", {
                "call_id": ctx.call_id,
                "question": question,
                "options": options,
                "session_id": ctx.session_id,
            })

        # If no job context or not interactive — degrade gracefully
        if job is None or not job.interactive:
            return ToolResult(
                output=f"[No user connected] Question asked: {question}",
                title="Question (no listener)",
                metadata={"question": question, "options": options},
            )

        # Block until user responds via POST /api/chat/respond
        try:
            response = await job.wait_for_response(ctx.call_id, timeout=300.0)
            return ToolResult(
                output=str(response),
                title=f"User answered: {str(response)[:100]}",
                metadata={"question": question, "answer": response},
            )
        except TimeoutError:
            return ToolResult(
                output="(user did not respond within 5 minutes)",
                error="Question timed out — no response from user",
            )
