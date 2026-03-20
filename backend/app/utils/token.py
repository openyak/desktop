"""Token counting utilities."""

from __future__ import annotations

import tiktoken

_encoding: tiktoken.Encoding | None = None


def _get_encoding() -> tiktoken.Encoding:
    global _encoding
    if _encoding is None:
        _encoding = tiktoken.get_encoding("cl100k_base")
    return _encoding


def count_tokens(text: str) -> int:
    """Count tokens using cl100k_base encoding (reasonable approximation for most models)."""
    return len(_get_encoding().encode(text))


def estimate_tokens(text: str) -> int:
    """Fast token estimate without full encoding (~4 chars per token)."""
    return max(1, len(text) // 4)
