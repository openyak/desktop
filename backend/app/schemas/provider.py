"""Provider and model schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ModelCapabilities(BaseModel):
    """What a model supports."""

    function_calling: bool = False
    vision: bool = False
    reasoning: bool = False
    json_output: bool = False
    max_context: int = 4096
    max_output: int | None = None
    prompt_caching: bool = False  # Whether model supports prompt caching


class ModelPricing(BaseModel):
    """Per-million-token pricing info (USD)."""

    prompt: float = 0.0  # Cost per million prompt tokens
    completion: float = 0.0  # Cost per million completion tokens


class ModelInfo(BaseModel):
    """A model available through a provider."""

    id: str
    name: str
    provider_id: str
    capabilities: ModelCapabilities = ModelCapabilities()
    pricing: ModelPricing = ModelPricing()
    metadata: dict[str, Any] = {}


class ProviderStatus(BaseModel):
    """Health status of a provider."""

    status: str  # "connected" | "error" | "unconfigured"
    model_count: int = 0
    error: str | None = None


class StreamChunk(BaseModel):
    """A single chunk from LLM streaming."""

    type: str  # "text-delta", "reasoning-delta", "tool-call", "usage", "finish", "error"
    data: dict[str, Any] = {}


class ApiKeyUpdate(BaseModel):
    """Request to update the OpenRouter API key."""

    api_key: str


class ApiKeyStatus(BaseModel):
    """API key configuration status."""

    is_configured: bool = False
    masked_key: str | None = None
    is_valid: bool | None = None
