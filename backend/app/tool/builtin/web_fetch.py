"""Web fetch tool — fetch URL content and convert to text."""

from __future__ import annotations

from typing import Any

import httpx

from app.tool.base import ToolDefinition, ToolResult
from app.tool.context import ToolContext


class WebFetchTool(ToolDefinition):

    @property
    def id(self) -> str:
        return "web_fetch"

    @property
    def description(self) -> str:
        return (
            "Fetch content from a URL and return it as text. "
            "Useful for reading documentation, API responses, and web pages."
        )

    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The URL to fetch",
                },
                "max_length": {
                    "type": "integer",
                    "description": "Maximum content length to return (default: 50000)",
                    "default": 50000,
                },
            },
            "required": ["url"],
        }

    async def execute(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        url = args["url"]
        max_length = args.get("max_length", 50000)

        try:
            async with httpx.AsyncClient(
                follow_redirects=True,
                timeout=30.0,
            ) as client:
                resp = await client.get(url, headers={
                    "User-Agent": "OpenYak/0.1 (tool; web_fetch)",
                })
                resp.raise_for_status()

            content_type = resp.headers.get("content-type", "")
            text = resp.text

            # Basic HTML stripping (simple approach)
            if "html" in content_type:
                text = _strip_html(text)

            if len(text) > max_length:
                text = text[:max_length] + f"\n\n... [truncated at {max_length} chars]"

            return ToolResult(
                output=text,
                title=f"Fetched {url[:60]}",
                metadata={"url": url, "status_code": resp.status_code, "length": len(text)},
            )

        except httpx.HTTPStatusError as e:
            return ToolResult(error=f"HTTP {e.response.status_code}: {url}")
        except httpx.RequestError as e:
            return ToolResult(error=f"Request failed: {e}")


def _strip_html(html: str) -> str:
    """Very basic HTML tag removal."""
    import re

    # Remove script and style blocks
    text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
    # Remove tags
    text = re.sub(r"<[^>]+>", " ", text)
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text
