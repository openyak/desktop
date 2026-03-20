"""Search tool — full-text search across workspace files using built-in FTS5.

Complements grep (exact regex) with ranked full-text keyword search.
"""

from __future__ import annotations

import logging
from typing import Any

from app.tool.base import ToolDefinition, ToolResult
from app.tool.context import ToolContext

logger = logging.getLogger(__name__)


class SearchTool(ToolDefinition):

    @property
    def id(self) -> str:
        return "search"

    @property
    def description(self) -> str:
        return (
            "Full-text search across all workspace files. "
            "Finds relevant files and passages by keyword. "
            "Returns ranked results with file paths and context snippets. "
            "Use this for broad discovery; use grep for exact pattern matching."
        )

    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Keywords or natural language search query",
                },
                "path": {
                    "type": "string",
                    "description": "Limit search to a subdirectory (optional)",
                },
                "file_types": {
                    "type": "string",
                    "description": "Comma-separated file extensions to include (e.g. 'py,ts,md')",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results to return",
                    "default": 20,
                },
            },
            "required": ["query"],
        }

    async def execute(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        index_manager = getattr(ctx, "index_manager", None)
        if index_manager is None:
            return ToolResult(
                error="Search tool requires FTS indexing to be enabled. "
                      "Set OPENYAK_FTS_ENABLED=true and select a workspace."
            )

        workspace = ctx.workspace
        if not workspace:
            return ToolResult(error="No workspace set for this session.")

        query = args["query"]
        search_path = args.get("path")
        file_types = args.get("file_types")
        max_results = args.get("max_results", 20)

        try:
            data = await index_manager.search(
                workspace,
                query,
                path_filter=search_path,
                file_types=file_types,
                limit=max_results,
            )
        except Exception as e:
            logger.error("FTS search failed: %s", e)
            return ToolResult(error=f"Search failed: {e}")

        results = data.get("results", [])
        if not results:
            return ToolResult(
                output="(no results)",
                title=f'No results for "{query}"',
                metadata={"count": 0},
            )

        lines = []
        for rank, match in enumerate(results, 1):
            filename = match.get("filename", "")
            highlight = (match.get("highlight") or "").strip()
            score = match.get("relevance_score")

            header = f"{rank}. {filename}"
            if score is not None:
                header += f"  [score: {score:.3f}]"
            lines.append(header)
            if highlight:
                lines.append(f"   {highlight}")
            lines.append("")

        output = "\n".join(lines).rstrip()
        return ToolResult(
            output=output,
            title=f'{len(results)} results for "{query}"',
            metadata={"count": len(results), "total": data.get("total", len(results)), "query": query, "source": "fts"},
        )
