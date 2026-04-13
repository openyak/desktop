"""Async message bus for decoupled channel-agent communication.

Ported from nanobot.bus (MIT license).
"""

from app.channels.bus.events import InboundMessage, OutboundMessage
from app.channels.bus.queue import MessageBus

__all__ = ["InboundMessage", "MessageBus", "OutboundMessage"]
