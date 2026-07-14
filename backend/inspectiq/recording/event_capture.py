"""ADB device touch/key event monitor for manual recording."""

from __future__ import annotations

import asyncio
import re
import time
from typing import Callable, Dict, Optional

from inspectiq.adb.manager import AdbManager
from inspectiq.logging_config import get_logger
from inspectiq.recording.interfaces import EventCaptureService
from inspectiq.recording.models import RecordedActionType
from inspectiq.recording.touch_calibration import TouchCalibration

logger = get_logger(__name__)

TouchCallback = Callable[[str, int, int, RecordedActionType], None]

_HEX_VALUE = re.compile(r"([0-9a-fx]+)$", re.I)
_DEBOUNCE_SEC = 0.35


class AdbEventCaptureService(EventCaptureService):
    """Monitors `adb shell getevent` for touch and key events during recording."""

    def __init__(self):
        self._adb = AdbManager()
        self._tasks: Dict[str, asyncio.Task] = {}
        self._running: Dict[str, bool] = {}
        self._calibration: Dict[str, TouchCalibration] = {}
        self._last_tap: Dict[str, tuple[float, int, int]] = {}

    async def start_device_monitor(self, device_id: str, callback: TouchCallback) -> None:
        if device_id in self._tasks and not self._tasks[device_id].done():
            return
        self._running[device_id] = True
        self._calibration[device_id] = await self._load_calibration(device_id)
        self._tasks[device_id] = asyncio.create_task(self._monitor_loop(device_id, callback))
        logger.info(
            "Device event monitor started: %s screen=%dx%d touch_max=%dx%d",
            device_id,
            self._calibration[device_id].screen_width,
            self._calibration[device_id].screen_height,
            self._calibration[device_id].raw_max_x,
            self._calibration[device_id].raw_max_y,
        )

    async def stop_device_monitor(self, device_id: str) -> None:
        self._running[device_id] = False
        task = self._tasks.pop(device_id, None)
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        self._calibration.pop(device_id, None)
        self._last_tap.pop(device_id, None)
        logger.info("Device event monitor stopped: %s", device_id)

    async def _load_calibration(self, device_id: str) -> TouchCalibration:
        try:
            _, props, _ = await self._adb.run("shell", "getevent", "-p", device_id=device_id, timeout=8.0)
            _, wm_size, _ = await self._adb.run("shell", "wm", "size", device_id=device_id, timeout=5.0)
            return TouchCalibration.from_getevent_props(props, wm_size)
        except Exception as exc:
            logger.warning("Touch calibration failed for %s: %s — using defaults", device_id, exc)
            return TouchCalibration()

    async def _monitor_loop(self, device_id: str, callback: TouchCallback) -> None:
        cal = self._calibration.get(device_id, TouchCalibration())
        raw_x = 0
        raw_y = 0
        finger_down = False
        pending_lift = False
        proc: Optional[asyncio.subprocess.Process] = None
        try:
            proc = await asyncio.create_subprocess_exec(
                self._adb.adb_path, "-s", device_id, "shell", "getevent", "-l",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            assert proc.stdout
            while self._running.get(device_id) and proc.returncode is None:
                try:
                    line = await asyncio.wait_for(proc.stdout.readline(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue
                if not line:
                    if proc.returncode is not None:
                        break
                    continue
                text = line.decode("utf-8", errors="replace").strip()
                if not text:
                    continue

                if "ABS_MT_POSITION_X" in text:
                    val = _parse_hex_value(text)
                    if val is not None:
                        raw_x = val
                elif "ABS_MT_POSITION_Y" in text:
                    val = _parse_hex_value(text)
                    if val is not None:
                        raw_y = val
                elif "ABS_X" in text and "ABS_MT" not in text:
                    val = _parse_hex_value(text)
                    if val is not None:
                        raw_x = val
                elif "ABS_Y" in text and "ABS_MT" not in text:
                    val = _parse_hex_value(text)
                    if val is not None:
                        raw_y = val
                elif "ABS_MT_TRACKING_ID" in text:
                    val = _parse_hex_value(text)
                    if val is not None:
                        if val == 0xFFFFFFFF or val == 0xFFFFFFFFFFFFFFFF:
                            pending_lift = True
                        else:
                            finger_down = True
                            pending_lift = False
                elif "BTN_TOUCH" in text and "DOWN" in text:
                    finger_down = True
                    pending_lift = False
                elif "BTN_TOUCH" in text and "UP" in text and finger_down:
                    pending_lift = True
                elif "KEY_BACK" in text and "DOWN" in text:
                    callback(device_id, 0, 0, RecordedActionType.PRESS_BACK)
                elif "KEY_HOME" in text and "DOWN" in text:
                    callback(device_id, 0, 0, RecordedActionType.PRESS_HOME)
                elif "KEY_APPSELECT" in text and "DOWN" in text:
                    callback(device_id, 0, 0, RecordedActionType.PRESS_RECENT)
                elif "SYN_REPORT" in text and pending_lift and finger_down:
                    sx, sy = cal.to_screen(raw_x, raw_y)
                    if self._should_emit_tap(device_id, sx, sy):
                        callback(device_id, sx, sy, RecordedActionType.TAP)
                    finger_down = False
                    pending_lift = False
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.warning("Device monitor error %s: %s", device_id, exc)
        finally:
            if proc is not None and proc.returncode is None:
                proc.terminate()
                try:
                    await asyncio.wait_for(proc.wait(), timeout=2.0)
                except asyncio.TimeoutError:
                    proc.kill()

    def _should_emit_tap(self, device_id: str, x: int, y: int) -> bool:
        now = time.monotonic()
        last = self._last_tap.get(device_id)
        if last and now - last[0] < _DEBOUNCE_SEC and abs(last[1] - x) < 8 and abs(last[2] - y) < 8:
            return False
        self._last_tap[device_id] = (now, x, y)
        return True

    async def inject_back(self, device_id: str) -> None:
        await self._adb.run("shell", "input", "keyevent", "4", device_id=device_id)

    async def inject_home(self, device_id: str) -> None:
        await self._adb.run("shell", "input", "keyevent", "3", device_id=device_id)

    async def inject_swipe(
        self, device_id: str, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300
    ) -> None:
        await self._adb.run(
            "shell", "input", "swipe",
            str(x1), str(y1), str(x2), str(y2), str(duration_ms),
            device_id=device_id,
        )


def _parse_hex_value(text: str) -> int | None:
    m = _HEX_VALUE.search(text)
    if not m:
        return None
    token = m.group(1)
    if token.startswith("0x") or token.startswith("0X"):
        return int(token, 16)
    try:
        return int(token, 16)
    except ValueError:
        return int(token)
