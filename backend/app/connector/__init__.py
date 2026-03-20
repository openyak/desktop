"""Connector layer — deduplicated MCP server management.

Connectors are independent of plugins. A plugin may *reference*
connectors, but each connector is a standalone entity that users
can enable/disable and connect/disconnect individually.
"""

from app.connector.model import ConnectorInfo
from app.connector.registry import ConnectorRegistry

__all__ = ["ConnectorInfo", "ConnectorRegistry"]
