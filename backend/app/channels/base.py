"""Base channel interface for chat platforms.

Ported from nanobot.channels.base (MIT license).
Adapted for OpenYak: removed loguru dependency, uses stdlib logging.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

from app.channels.bus.events import InboundMessage, OutboundMessage
from app.channels.bus.queue import MessageBus

logger = logging.getLogger(__name__)


class BaseChannel(ABC):
    """
    Abstract base class for chat channel implementations.

    Each channel (Telegram, Discord, etc.) should implement this interface
    to integrate with the OpenYak message bus.
    """

    name: str = "base"
    display_name: str = "Base"

    def __init__(self, config: Any, bus: MessageBus):
        self.config = config
        self.bus = bus
        self._running = False

    async def login(self, force: bool = False) -> bool:
        """Perform channel-specific interactive login (e.g. QR code scan).

        Returns True if already authenticated or login succeeds.
        Override in subclasses that support interactive login.
        """
        return True

    @abstractmethod
    async def start(self) -> None:
        """Start the channel and begin listening for messages."""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """Stop the channel and clean up resources."""
        pass

    @abstractmethod
    async def send(self, msg: OutboundMessage) -> None:
        """Send a message through this channel."""
        pass

    async def send_delta(self, chat_id: str, delta: str, metadata: dict[str, Any] | None = None) -> None:
        """Deliver a streaming text chunk. Override in subclasses."""
        pass

    @property
    def supports_streaming(self) -> bool:
        """True when config enables streaming AND this subclass implements send_delta."""
        cfg = self.config
        streaming = cfg.get("streaming", False) if isinstance(cfg, dict) else getattr(cfg, "streaming", False)
        return bool(streaming) and type(self).send_delta is not BaseChannel.send_delta

    def is_allowed(self, sender_id: str) -> bool:
        """Check if sender_id is permitted. Empty list -> deny all; '*' -> allow all."""
        allow_list = getattr(self.config, "allow_from", None)
        if allow_list is None and isinstance(self.config, dict):
            allow_list = self.config.get("allow_from", [])
        if not allow_list:
            logger.warning("%s: allow_from is empty — all access denied", self.name)
            return False
        if "*" in allow_list:
            return True
        return str(sender_id) in allow_list

    async def _handle_message(
        self,
        sender_id: str,
        chat_id: str,
        content: str,
        media: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        session_key: str | None = None,
    ) -> None:
        """Handle an incoming message from the chat platform."""
        if not self.is_allowed(sender_id):
            logger.warning(
                "Access denied for sender %s on channel %s. "
                "Add them to allow_from list in config to grant access.",
                sender_id, self.name,
            )
            return

        meta = metadata or {}
        if self.supports_streaming:
            meta = {**meta, "_wants_stream": True}

        msg = InboundMessage(
            channel=self.name,
            sender_id=str(sender_id),
            chat_id=str(chat_id),
            content=content,
            media=media or [],
            metadata=meta,
            session_key_override=session_key,
        )

        await self.bus.publish_inbound(msg)

    @classmethod
    def default_config(cls) -> dict[str, Any]:
        """Return default config for onboard. Override in plugins."""
        return {"enabled": False}

    @property
    def is_running(self) -> bool:
        return self._running
