"""WebSocket live UI refresh for connected device sessions."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, Optional

from fastapi import WebSocket, WebSocketDisconnect

from inspectiq.domain.models import Platform
from inspectiq.services.inspection_service import InspectionService

logger = logging.getLogger(__name__)


class LiveRefreshManager:
    """Manages WebSocket connections and periodic UI tree refresh."""

    def __init__(self, inspection: InspectionService):
        self.inspection = inspection
        self.active_tasks: Dict[str, asyncio.Task] = {}

    async def handle(self, websocket: WebSocket) -> None:
        await websocket.accept()
        device_id: Optional[str] = None
        task_key: Optional[str] = None

        try:
            while True:
                raw = await websocket.receive_text()
                msg = json.loads(raw)
                action = msg.get("action")

                if action == "subscribe":
                    device_id = msg["device_id"]
                    platform = Platform(msg.get("platform", "android"))
                    interval = float(msg.get("interval", 2.0))
                    interval = max(0.5, min(interval, 30.0))
                    task_key = f"{device_id}:{platform.value}"

                    if task_key in self.active_tasks:
                        self.active_tasks[task_key].cancel()

                    task = asyncio.create_task(
                        self._refresh_loop(websocket, device_id, platform, interval)
                    )
                    self.active_tasks[task_key] = task

                    await websocket.send_json({
                        "type": "subscribed",
                        "device_id": device_id,
                        "interval": interval,
                    })

                elif action == "unsubscribe":
                    if task_key and task_key in self.active_tasks:
                        self.active_tasks[task_key].cancel()
                        del self.active_tasks[task_key]
                    await websocket.send_json({"type": "unsubscribed"})

                elif action == "refresh_once":
                    device_id = msg["device_id"]
                    platform = Platform(msg.get("platform", "android"))
                    session = await self.inspection.refresh_session(device_id, platform)
                    await websocket.send_json({
                        "type": "session_update",
                        "session": session.model_dump(mode="json"),
                    })

        except WebSocketDisconnect:
            logger.debug("WebSocket disconnected: %s", device_id)
        except Exception as exc:
            logger.exception("WebSocket error: %s", exc)
            try:
                await websocket.send_json({"type": "error", "message": str(exc)})
            except Exception:
                pass
        finally:
            if task_key and task_key in self.active_tasks:
                self.active_tasks[task_key].cancel()
                del self.active_tasks[task_key]

    async def _refresh_loop(
        self,
        websocket: WebSocket,
        device_id: str,
        platform: Platform,
        interval: float,
    ) -> None:
        while True:
            try:
                session = await self.inspection.refresh_session(device_id, platform)
                await websocket.send_json({
                    "type": "session_update",
                    "session": session.model_dump(mode="json"),
                })
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                await websocket.send_json({
                    "type": "error",
                    "message": str(exc),
                })
            await asyncio.sleep(interval)
