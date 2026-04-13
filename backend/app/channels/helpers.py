"""Helper utilities for channel implementations.

Provides path helpers and text utilities that replace nanobot's
config.paths, utils.helpers, and security.network modules.
"""

from __future__ import annotations

import ipaddress
import logging
import re
import unicodedata
from pathlib import Path
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Base data directory for channels (relative to backend working dir)
_DATA_DIR = Path("data")


def get_data_dir() -> Path:
    """Return the base data directory."""
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    return _DATA_DIR


def get_media_dir(channel: str) -> Path:
    """Return a per-channel media download directory."""
    d = _DATA_DIR / "media" / channel
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_runtime_subdir(name: str) -> Path:
    """Return a runtime subdirectory (e.g. for auth tokens)."""
    d = _DATA_DIR / "runtime" / name
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_bridge_install_dir() -> Path:
    """Return the directory for the WhatsApp bridge installation."""
    d = _DATA_DIR / "bridge"
    d.mkdir(parents=True, exist_ok=True)
    return d


def split_message(text: str, max_len: int) -> list[str]:
    """Split a message into chunks that fit within max_len.

    Tries to split at newlines or sentence boundaries first.
    """
    if len(text) <= max_len:
        return [text]

    chunks: list[str] = []
    while text:
        if len(text) <= max_len:
            chunks.append(text)
            break

        # Try to split at last newline within limit
        split_at = text.rfind("\n", 0, max_len)
        if split_at <= 0:
            # Try to split at last space
            split_at = text.rfind(" ", 0, max_len)
        if split_at <= 0:
            # Hard split
            split_at = max_len

        chunks.append(text[:split_at])
        text = text[split_at:].lstrip("\n")

    return chunks


def safe_filename(name: str) -> str:
    """Sanitize a filename, removing unsafe characters."""
    if not name:
        return ""
    # Remove path separators and null bytes
    name = name.replace("/", "_").replace("\\", "_").replace("\x00", "")
    # Remove other unsafe characters
    name = re.sub(r'[<>:"|?*]', "_", name)
    # Normalize unicode
    name = unicodedata.normalize("NFC", name)
    # Limit length
    if len(name) > 200:
        name = name[:200]
    return name.strip(". ")


def validate_url_target(url: str) -> tuple[bool, str]:
    """Basic SSRF check — block private/loopback IPs.

    Returns (ok, error_message).
    """
    try:
        parsed = urlparse(url)
        host = parsed.hostname
        if not host:
            return False, "No hostname in URL"

        # Check if it's an IP address
        try:
            ip = ipaddress.ip_address(host)
            if ip.is_private or ip.is_loopback or ip.is_reserved:
                return False, f"Blocked private/loopback IP: {host}"
        except ValueError:
            # It's a hostname, not an IP — allow it
            pass

        return True, ""
    except Exception as e:
        return False, str(e)


def build_help_text() -> str:
    """Return a simple help text for chat commands."""
    return (
        "Available commands:\n"
        "/help - Show this help message\n"
        "/stop - Stop the current response\n"
    )
