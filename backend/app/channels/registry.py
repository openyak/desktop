"""Auto-discovery for built-in channel modules.

Ported from nanobot.channels.registry (MIT license).
Adapted for OpenYak: uses stdlib logging, scans app.channels package.
"""

from __future__ import annotations

import importlib
import logging
import pkgutil
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.channels.base import BaseChannel

logger = logging.getLogger(__name__)

# Internal modules that are not channel implementations
_INTERNAL = frozenset({"base", "manager", "registry", "adapter", "config", "bus"})


def discover_channel_names() -> list[str]:
    """Return all built-in channel module names by scanning the package."""
    import app.channels as pkg

    return [
        name
        for _, name, ispkg in pkgutil.iter_modules(pkg.__path__)
        if name not in _INTERNAL and not ispkg
    ]


def load_channel_class(module_name: str) -> type[BaseChannel]:
    """Import module_name and return the first BaseChannel subclass found."""
    from app.channels.base import BaseChannel as _Base

    mod = importlib.import_module(f"app.channels.{module_name}")
    for attr in dir(mod):
        obj = getattr(mod, attr)
        if isinstance(obj, type) and issubclass(obj, _Base) and obj is not _Base:
            return obj
    raise ImportError(f"No BaseChannel subclass in app.channels.{module_name}")


def discover_all() -> dict[str, type[BaseChannel]]:
    """Return all available channel classes keyed by module name."""
    result: dict[str, type[BaseChannel]] = {}
    for modname in discover_channel_names():
        try:
            result[modname] = load_channel_class(modname)
        except (ImportError, Exception) as e:
            logger.debug("Skipping channel '%s': %s", modname, e)
    return result
