"""Auto-generate session title using the title agent."""

from __future__ import annotations

import logging
from typing import Any

from app.agent.agent import AgentRegistry
from app.provider.registry import ProviderRegistry

logger = logging.getLogger(__name__)


async def generate_title(
    first_user_message: str,
    *,
    provider_registry: ProviderRegistry,
    agent_registry: AgentRegistry,
    model_id: str | None = None,
) -> str | None:
    """Generate a short title for a session based on the first user message.

    Returns the title string or None on failure.
    """
    title_agent = agent_registry.get("title")
    if not title_agent or not title_agent.system_prompt:
        return None

    # Find a model to use
    if not model_id:
        models = provider_registry.all_models()
        if not models:
            return None
        model_id = models[0].id

    resolved = provider_registry.resolve_model(model_id)
    if not resolved:
        return None

    provider, _ = resolved

    try:
        messages = [{"role": "user", "content": first_user_message}]
        title = ""

        async for chunk in provider.stream_chat(
            model_id,
            messages,
            system=title_agent.system_prompt,
            temperature=title_agent.temperature,
            max_tokens=64,
        ):
            if chunk.type == "text-delta":
                title += chunk.data.get("text", "")

        # Clean up
        title = title.strip().strip('"').strip("'").strip()
        if title:
            return title[:100]  # Limit length

    except Exception as e:
        logger.warning("Failed to generate title: %s", e)

    return None
