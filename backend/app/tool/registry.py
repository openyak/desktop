"""Tool registry — manages tool instances and per-agent filtering."""

from __future__ import annotations

import logging
from typing import Any

from app.agent.permission import evaluate, merge_rulesets
from app.schemas.agent import AgentInfo, Ruleset
from app.tool.base import ToolDefinition

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Central registry for all tool definitions."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, tool: ToolDefinition) -> None:
        """Register a tool."""
        self._tools[tool.id] = tool
        logger.debug("Registered tool: %s", tool.id)

    def unregister(self, tool_id: str) -> None:
        """Remove a tool by ID."""
        self._tools.pop(tool_id, None)

    def get(self, tool_id: str) -> ToolDefinition | None:
        """Get a tool by ID."""
        return self._tools.get(tool_id)

    def all_tools(self) -> list[ToolDefinition]:
        """List all registered tools."""
        return list(self._tools.values())

    def resolve_for_agent(
        self,
        agent: AgentInfo,
        *,
        extra_ruleset: Ruleset | None = None,
        exclude: set[str] | None = None,
    ) -> list[ToolDefinition]:
        """Get tools available to an agent, filtered by permissions.

        If agent.tools is non-empty, only those tools are considered.
        Then permission rules further filter the set.
        ``exclude`` silently removes tools (e.g. quota-exceeded tools).
        """
        # Start with agent's tool whitelist or all tools
        if agent.tools:
            candidates = [
                self._tools[tid]
                for tid in agent.tools
                if tid in self._tools
            ]
        else:
            candidates = list(self._tools.values())

        # Filter by permissions
        ruleset = agent.permissions
        if extra_ruleset:
            ruleset = merge_rulesets(ruleset, extra_ruleset)

        result = [
            tool for tool in candidates
            if evaluate(tool.id, "*", ruleset) != "deny"
        ]

        if exclude:
            result = [t for t in result if t.id not in exclude]

        return result

    def to_openai_specs(
        self,
        agent: AgentInfo,
        *,
        extra_ruleset: Ruleset | None = None,
        exclude: set[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Get OpenAI function specs for tools available to an agent."""
        tools = self.resolve_for_agent(agent, extra_ruleset=extra_ruleset, exclude=exclude)
        return [tool.to_openai_spec() for tool in tools]
