"""Channel manager for coordinating chat channels.

Ported from nanobot.channels.manager (MIT license).
Adapted for OpenYak: uses ChannelsConfig instead of nanobot Config,
stdlib logging instead of loguru.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.channels.base import BaseChannel
from app.channels.bus.events import OutboundMessage
from app.channels.bus.queue import MessageBus
from app.channels.config import ChannelsConfig

logger = logging.getLogger(__name__)

# Retry delays for message sending (exponential backoff: 1s, 2s, 4s)
_SEND_RETRY_DELAYS = (1, 2, 4)


class ChannelManager:
    """
    Manages chat channels and coordinates message routing.

    Responsibilities:
    - Initialize enabled channels (Telegram, WhatsApp, etc.)
    - Start/stop channels
    - Route outbound messages
    """

    def __init__(self, config: ChannelsConfig, bus: MessageBus):
        self.config = config
        self.bus = bus
        self.channels: dict[str, BaseChannel] = {}
        self._dispatch_task: asyncio.Task | None = None
        self._channel_tasks: list[asyncio.Task] = []

    def init_channels(self) -> None:
        """Initialize channels from config. Call after construction."""
        from app.channels.registry import discover_all

        for name, cls in discover_all().items():
            section = self.config.channels.get(name)
            if section is None:
                continue
            enabled = section.get("enabled", False)
            if not enabled:
                continue
            try:
                channel = cls(section, self.bus)
                self.channels[name] = channel
                logger.info("%s channel enabled", cls.display_name)
            except Exception as e:
                logger.warning("%s channel not available: %s", name, e)

    def add_channel(self, name: str, channel: BaseChannel) -> None:
        """Dynamically add a channel (e.g. from API)."""
        self.channels[name] = channel

    def remove_channel(self, name: str) -> None:
        """Remove a channel by name."""
        self.channels.pop(name, None)

    async def _start_channel(self, name: str, channel: BaseChannel) -> None:
        """Start a channel and log any exceptions."""
        try:
            await channel.start()
        except Exception as e:
            logger.error("Failed to start channel %s: %s", name, e)

    async def start_all(self) -> None:
        """Start all channels and the outbound dispatcher."""
        if not self.channels:
            logger.warning("No channels enabled")
            return

        # Start outbound dispatcher
        self._dispatch_task = asyncio.create_task(self._dispatch_outbound())

        # Start channels
        for name, channel in self.channels.items():
            logger.info("Starting %s channel...", name)
            task = asyncio.create_task(self._start_channel(name, channel))
            self._channel_tasks.append(task)

    async def stop_all(self) -> None:
        """Stop all channels and the dispatcher."""
        logger.info("Stopping all channels...")

        # Stop dispatcher
        if self._dispatch_task:
            self._dispatch_task.cancel()
            try:
                await self._dispatch_task
            except asyncio.CancelledError:
                pass

        # Cancel channel tasks
        for task in self._channel_tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        self._channel_tasks.clear()

        # Stop all channels
        for name, channel in self.channels.items():
            try:
                await channel.stop()
                logger.info("Stopped %s channel", name)
            except Exception as e:
                logger.error("Error stopping %s: %s", name, e)

    async def _dispatch_outbound(self) -> None:
        """Dispatch outbound messages to the appropriate channel."""
        logger.info("Outbound dispatcher started")

        pending: list[OutboundMessage] = []

        while True:
            try:
                if pending:
                    msg = pending.pop(0)
                else:
                    msg = await asyncio.wait_for(
                        self.bus.consume_outbound(),
                        timeout=1.0,
                    )

                if msg.metadata.get("_progress"):
                    if msg.metadata.get("_tool_hint") and not self.config.send_tool_hints:
                        continue
                    if not msg.metadata.get("_tool_hint") and not self.config.send_progress:
                        continue

                # Coalesce consecutive _stream_delta messages
                if msg.metadata.get("_stream_delta") and not msg.metadata.get("_stream_end"):
                    msg, extra_pending = self._coalesce_stream_deltas(msg)
                    pending.extend(extra_pending)

                channel = self.channels.get(msg.channel)
                if channel:
                    await self._send_with_retry(channel, msg)
                else:
                    logger.warning("Unknown channel: %s", msg.channel)

            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break

    @staticmethod
    async def _send_once(channel: BaseChannel, msg: OutboundMessage) -> None:
        """Send one outbound message without retry policy."""
        if msg.metadata.get("_stream_delta") or msg.metadata.get("_stream_end"):
            await channel.send_delta(msg.chat_id, msg.content, msg.metadata)
        elif not msg.metadata.get("_streamed"):
            await channel.send(msg)

    def _coalesce_stream_deltas(
        self, first_msg: OutboundMessage
    ) -> tuple[OutboundMessage, list[OutboundMessage]]:
        """Merge consecutive _stream_delta messages for the same (channel, chat_id)."""
        target_key = (first_msg.channel, first_msg.chat_id)
        combined_content = first_msg.content
        final_metadata = dict(first_msg.metadata or {})
        non_matching: list[OutboundMessage] = []

        while True:
            try:
                next_msg = self.bus.outbound.get_nowait()
            except asyncio.QueueEmpty:
                break

            same_target = (next_msg.channel, next_msg.chat_id) == target_key
            is_delta = next_msg.metadata and next_msg.metadata.get("_stream_delta")
            is_end = next_msg.metadata and next_msg.metadata.get("_stream_end")

            if same_target and is_delta and not final_metadata.get("_stream_end"):
                combined_content += next_msg.content
                if is_end:
                    final_metadata["_stream_end"] = True
                    break
            else:
                non_matching.append(next_msg)
                break

        merged = OutboundMessage(
            channel=first_msg.channel,
            chat_id=first_msg.chat_id,
            content=combined_content,
            metadata=final_metadata,
        )
        return merged, non_matching

    async def _send_with_retry(self, channel: BaseChannel, msg: OutboundMessage) -> None:
        """Send a message with retry on failure using exponential backoff."""
        max_attempts = max(self.config.send_max_retries, 1)

        for attempt in range(max_attempts):
            try:
                await self._send_once(channel, msg)
                return
            except asyncio.CancelledError:
                raise
            except Exception as e:
                if attempt == max_attempts - 1:
                    logger.error(
                        "Failed to send to %s after %d attempts: %s - %s",
                        msg.channel, max_attempts, type(e).__name__, e,
                    )
                    return
                delay = _SEND_RETRY_DELAYS[min(attempt, len(_SEND_RETRY_DELAYS) - 1)]
                logger.warning(
                    "Send to %s failed (attempt %d/%d): %s, retrying in %ds",
                    msg.channel, attempt + 1, max_attempts, type(e).__name__, delay,
                )
                try:
                    await asyncio.sleep(delay)
                except asyncio.CancelledError:
                    raise

    def get_channel(self, name: str) -> BaseChannel | None:
        return self.channels.get(name)

    def get_status(self) -> dict[str, Any]:
        """Get status of all channels."""
        return {
            name: {
                "enabled": True,
                "running": channel.is_running,
            }
            for name, channel in self.channels.items()
        }

    @property
    def enabled_channels(self) -> list[str]:
        return list(self.channels.keys())
