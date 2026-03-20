"""Remote access token generation, storage, and validation.

Tokens are simple Bearer secrets (not JWT) — appropriate for a single-user
desktop app where the owner generates a token and shares it with their own phone.
"""

from __future__ import annotations

import json
import logging
import secrets
from pathlib import Path

logger = logging.getLogger(__name__)

_TOKEN_PREFIX = "openyak_rt_"


def generate_token() -> str:
    """Generate a cryptographically random remote access token (256-bit)."""
    return _TOKEN_PREFIX + secrets.token_urlsafe(32)


def save_token(token: str, path: Path) -> None:
    """Persist token to disk."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"token": token}), encoding="utf-8")
    logger.info("Remote access token saved to %s", path)


def load_token(path: Path) -> str | None:
    """Load token from disk, or return None if not found."""
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data.get("token")
    except (json.JSONDecodeError, KeyError, OSError) as e:
        logger.warning("Failed to load remote token from %s: %s", path, e)
        return None


def delete_token(path: Path) -> None:
    """Delete token file."""
    if path.exists():
        path.unlink()
        logger.info("Remote access token deleted")


def rotate_token(path: Path) -> str:
    """Generate a new token, replacing the old one."""
    token = generate_token()
    save_token(token, path)
    return token


def validate_token(provided: str, expected: str) -> bool:
    """Constant-time token comparison to prevent timing attacks."""
    return secrets.compare_digest(provided, expected)
