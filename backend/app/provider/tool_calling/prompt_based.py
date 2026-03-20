"""Prompt-based tool calling fallback for non-FC models.

For models that don't support OpenAI-style function calling,
we inject tool descriptions into the system prompt and parse
<tool_call> tags from the model's text output.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from app.schemas.provider import StreamChunk
from app.tool.base import ToolDefinition

logger = logging.getLogger(__name__)

# Template for injecting tool descriptions into system prompt
TOOL_PROMPT_TEMPLATE = """
# Available Tools

You have access to the following tools. To use a tool, output a tool call in this exact format:

<tool_call>
{{"name": "tool_name", "arguments": {{"arg1": "value1", "arg2": "value2"}}}}
</tool_call>

You can make multiple tool calls in a single response. After each tool call, you will receive the result.

## Tools

{tool_descriptions}

IMPORTANT: Only use the exact tool names listed above. Always use the <tool_call> XML tag format.
"""


def build_tool_prompt(tools: list[ToolDefinition]) -> str:
    """Build tool description section for the system prompt."""
    descriptions = []
    for tool in tools:
        schema = tool.parameters_schema()
        props = schema.get("properties", {})
        required = schema.get("required", [])

        param_lines = []
        for name, prop in props.items():
            req = " (required)" if name in required else ""
            desc = prop.get("description", "")
            ptype = prop.get("type", "any")
            param_lines.append(f"    - {name}: {ptype}{req} — {desc}")

        params_str = "\n".join(param_lines) if param_lines else "    (no parameters)"

        descriptions.append(
            f"### {tool.id}\n{tool.description}\n\nParameters:\n{params_str}"
        )

    tool_text = "\n\n".join(descriptions)
    return TOOL_PROMPT_TEMPLATE.format(tool_descriptions=tool_text)


def parse_tool_calls(text: str) -> tuple[str, list[dict[str, Any]]]:
    """Parse <tool_call> tags from model output.

    Returns:
        (clean_text, tool_calls) where clean_text has tags removed
        and tool_calls is a list of {"name": ..., "arguments": ...}
    """
    pattern = re.compile(
        r"<tool_call>\s*(\{.*?\})\s*</tool_call>",
        re.DOTALL,
    )

    tool_calls = []
    for match in pattern.finditer(text):
        try:
            data = json.loads(match.group(1))
            name = data.get("name", "")
            arguments = data.get("arguments", {})
            if name:
                tool_calls.append({
                    "id": f"call_{len(tool_calls)}",
                    "name": name,
                    "arguments": arguments,
                })
        except json.JSONDecodeError:
            logger.warning("Failed to parse tool_call: %s", match.group(1)[:200])

    # Remove tool_call tags from text
    clean_text = pattern.sub("", text).strip()

    return clean_text, tool_calls


def convert_to_stream_chunks(
    text: str,
) -> list[StreamChunk]:
    """Convert accumulated text with potential tool calls into StreamChunks.

    Called when streaming is complete for prompt-based tool calling.
    Separates text content from tool calls.
    """
    clean_text, tool_calls = parse_tool_calls(text)

    chunks = []

    if clean_text:
        chunks.append(StreamChunk(type="text-delta", data={"text": clean_text}))

    for tc in tool_calls:
        chunks.append(StreamChunk(type="tool-call", data=tc))

    return chunks
