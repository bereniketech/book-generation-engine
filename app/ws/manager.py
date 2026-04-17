"""WebSocket connection manager."""
from __future__ import annotations

import json
import logging
from collections import defaultdict

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[str, list[WebSocket]] = defaultdict(list)

    async def connect(self, job_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections[job_id].append(websocket)
        logger.info("WS connected: job=%s total=%d", job_id, len(self._connections[job_id]))

    def disconnect(self, job_id: str, websocket: WebSocket) -> None:
        if websocket in self._connections[job_id]:
            self._connections[job_id].remove(websocket)

    async def broadcast(self, job_id: str, event: dict) -> None:
        dead: list[WebSocket] = []
        for ws in list(self._connections.get(job_id, [])):
            try:
                await ws.send_text(json.dumps(event))
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(job_id, ws)


manager = ConnectionManager()
