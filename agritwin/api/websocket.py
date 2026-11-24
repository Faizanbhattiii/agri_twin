"""
WebSocket Connection Manager for real-time sensor telemetry broadcasting.
"""

import logging
from typing import Any, Dict, List
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class TelemetryConnectionManager:
    """Manages active WebSocket clients and broadcasts telemetry updates."""

    def __init__(self) -> None:
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        """Accept and register a new WebSocket client."""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info("WebSocket client connected (active=%d)", len(self.active_connections))

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove a disconnected WebSocket client."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info("WebSocket client disconnected (active=%d)", len(self.active_connections))

    async def broadcast(self, message: Dict[str, Any]) -> None:
        """Broadcast a JSON telemetry message to all connected clients."""
        stale: List[WebSocket] = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as exc:
                logger.warning("Dropping failed WebSocket client: %s", exc)
                stale.append(connection)

        for conn in stale:
            self.disconnect(conn)


ws_manager = TelemetryConnectionManager()
