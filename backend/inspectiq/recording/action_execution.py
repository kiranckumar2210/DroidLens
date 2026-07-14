"""Execute recorder actions on a connected Android device via ADB (Appium-compatible semantics)."""

from __future__ import annotations

import asyncio
from typing import Optional

from inspectiq.adb.manager import AdbManager
from inspectiq.domain.models import Bounds, ElementNode
from inspectiq.logging_config import get_logger
from inspectiq.recording.interfaces import ActionExecutionService
from inspectiq.recording.models import RecordedActionType

logger = get_logger(__name__)

_SWIPE_DISTANCE = 400
_LONG_PRESS_MS = 800


class AdbActionExecutionService(ActionExecutionService):
    """Runs inspector-selected actions on the device using ADB shell input commands."""

    def __init__(self, adb: Optional[AdbManager] = None):
        self._adb = adb or AdbManager()

    async def execute(
        self,
        device_id: str,
        action_type: RecordedActionType,
        *,
        element: Optional[ElementNode] = None,
        x: Optional[int] = None,
        y: Optional[int] = None,
        text_value: Optional[str] = None,
        swipe_direction: Optional[str] = None,
    ) -> None:
        cx, cy = self._resolve_point(element, x, y)

        if action_type == RecordedActionType.TAP:
            await self._tap(device_id, cx, cy)
        elif action_type == RecordedActionType.DOUBLE_TAP:
            await self._tap(device_id, cx, cy)
            await asyncio.sleep(0.08)
            await self._tap(device_id, cx, cy)
        elif action_type == RecordedActionType.LONG_PRESS:
            await self._long_press(device_id, cx, cy)
        elif action_type == RecordedActionType.SET_TEXT:
            await self._tap(device_id, cx, cy)
            await asyncio.sleep(0.15)
            await self._set_text(device_id, text_value or "")
        elif action_type == RecordedActionType.CLEAR_TEXT:
            await self._tap(device_id, cx, cy)
            await asyncio.sleep(0.1)
            await self._adb.run("shell", "input", "keyevent", "123", device_id=device_id)  # MOVE_END
            await self._adb.run(
                "shell", "input", "keyevent", "--longpress", "67", device_id=device_id
            )  # DEL long
        elif action_type in (RecordedActionType.SWIPE, RecordedActionType.SCROLL):
            await self._swipe_direction(device_id, cx, cy, swipe_direction or "down")
        elif action_type == RecordedActionType.PRESS_BACK:
            await self._adb.run("shell", "input", "keyevent", "4", device_id=device_id)
        elif action_type == RecordedActionType.PRESS_HOME:
            await self._adb.run("shell", "input", "keyevent", "3", device_id=device_id)
        elif action_type == RecordedActionType.PRESS_RECENT:
            await self._adb.run("shell", "input", "keyevent", "187", device_id=device_id)
        elif action_type == RecordedActionType.OPEN_NOTIFICATION:
            await self._adb.run("shell", "cmd", "statusbar", "expand-notifications", device_id=device_id)
        elif action_type in (
            RecordedActionType.WAIT,
            RecordedActionType.WAIT_VISIBLE,
            RecordedActionType.WAIT_CLICKABLE,
            RecordedActionType.VERIFY_EXISTS,
            RecordedActionType.VERIFY_VISIBLE,
            RecordedActionType.VERIFY_ENABLED,
            RecordedActionType.VERIFY_TEXT,
            RecordedActionType.SCREENSHOT,
            RecordedActionType.CUSTOM,
        ):
            # Record-only actions — no device input required.
            return
        else:
            raise ValueError(f"Unsupported action execution: {action_type.value}")

    @staticmethod
    def _resolve_point(
        element: Optional[ElementNode], x: Optional[int], y: Optional[int]
    ) -> tuple[int, int]:
        if element and element.bounds:
            b = element.bounds
            return (b.x1 + b.x2) // 2, (b.y1 + b.y2) // 2
        if x is not None and y is not None:
            return x, y
        raise ValueError("Element or coordinates required for this action")

    async def _tap(self, device_id: str, x: int, y: int) -> None:
        await self._adb.run("shell", "input", "tap", str(x), str(y), device_id=device_id)

    async def _long_press(self, device_id: str, x: int, y: int) -> None:
        await self._adb.run(
            "shell", "input", "swipe",
            str(x), str(y), str(x), str(y), str(_LONG_PRESS_MS),
            device_id=device_id,
        )

    async def _set_text(self, device_id: str, text: str) -> None:
        escaped = text.replace(" ", "%s")
        await self._adb.run("shell", "input", "text", escaped, device_id=device_id)

    async def _swipe_direction(
        self, device_id: str, cx: int, cy: int, direction: str
    ) -> None:
        d = direction.lower()
        dist = _SWIPE_DISTANCE
        targets = {
            "up": (cx, cy + dist, cx, cy - dist),
            "down": (cx, cy - dist, cx, cy + dist),
            "left": (cx + dist, cy, cx - dist, cy),
            "right": (cx - dist, cy, cx + dist, cy),
        }
        x1, y1, x2, y2 = targets.get(d, targets["down"])
        await self._adb.run(
            "shell", "input", "swipe",
            str(x1), str(y1), str(x2), str(y2), "300",
            device_id=device_id,
        )
