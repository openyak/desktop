"""Detect native function calling support per model.

Some models support OpenAI-style function calling natively.
Others need prompt-based fallback with <tool_call> tags.
"""

from __future__ import annotations

from app.schemas.provider import ModelInfo

# Known patterns for models that support native function calling
FC_SUPPORTED_PATTERNS = [
    "glm-5",
    "glm-4.7",
    "claude",
    "gemini",
    "mistral",
    "command-r",
    "llama-3.1",
    "llama-3.2",
    "llama-3.3",
    "qwen",
    "deepseek",
]

# Models known to NOT support function calling
FC_UNSUPPORTED_PATTERNS = [
    "phi-2",
    "gemma-2b",
    "tinyllama",
    "stablelm",
]


def supports_function_calling(model: ModelInfo) -> bool:
    """Detect whether a model supports native function calling.

    Uses model capabilities from the provider first, then falls back
    to pattern matching on the model ID.
    """
    # Trust provider-reported capability
    if model.capabilities.function_calling:
        return True

    model_id_lower = model.id.lower()

    # Check unsupported patterns first
    for pattern in FC_UNSUPPORTED_PATTERNS:
        if pattern in model_id_lower:
            return False

    # Check supported patterns
    for pattern in FC_SUPPORTED_PATTERNS:
        if pattern in model_id_lower:
            return True

    # Default: assume not supported (safer — use prompt-based)
    return False
