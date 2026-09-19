import logging
from typing import Any

from fastapi import WebSocket


logger = logging.getLogger(__name__)


class WebsocketConnectionManager:

    def __init__(self):
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket) -> None:
        """Accept and register a WebSocket connection."""
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket) -> None:
        """Remove a connection if it is still registered."""
        if ws in self.active:
            self.active.remove(ws)

    async def broadcast(self, data: Any) -> None:
        """Broadcast data while isolating and removing failed clients."""
        for ws in self.active.copy():
            try:
                await ws.send_json(data)
            except Exception:
                # Delivery is best-effort: one failed client must not
                # prevent updates from reaching healthy clients.
                logger.warning(
                    "WebSocket broadcast failed; "
                    "removing stale client",
                    exc_info=True,
                )
                self.disconnect(ws)


ws_manager = WebsocketConnectionManager()