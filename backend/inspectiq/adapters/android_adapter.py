"""Android platform adapter — production ADB + UIAutomator."""

from __future__ import annotations

import asyncio
import base64
import re
from typing import List, Optional

from inspectiq.adapters.base import PlatformAdapter
from inspectiq.adb.manager import AdbError, AdbManager
from inspectiq.domain.models import Bounds, DeviceInfo, ElementNode, Platform
from inspectiq.engine.xml_parser import AndroidXmlParser


class AndroidAdapter(PlatformAdapter):
    platform = Platform.ANDROID

    def __init__(self, adb: Optional[AdbManager] = None):
        self._adb = adb or AdbManager()
        self._parser = AndroidXmlParser()

    async def list_devices(self) -> List[DeviceInfo]:
        try:
            return await self._adb.list_devices_detailed()
        except AdbError:
            return []

    async def connect(self, device_id: str) -> None:
        code, _, err = await self._adb.run("shell", "echo", "ok", device_id=device_id, timeout=10.0)
        if code != 0:
            raise ConnectionError(f"Cannot connect to Android device {device_id}: {err}")

    async def dump_ui(self, device_id: str) -> str:
        strategies = [
            self._dump_accessibility,
            self._dump_uiautomator_file,
            self._dump_uiautomator_tty,
        ]
        errors: list[str] = []
        for attempt in range(3):
            if attempt > 0:
                await asyncio.sleep(0.35 * attempt)
            for strategy in strategies:
                try:
                    xml = await strategy(device_id)
                    if xml and ("<?xml" in xml or "<hierarchy" in xml):
                        return xml
                except Exception as exc:
                    errors.append(str(exc))
        raise RuntimeError("UI dump failed. " + "; ".join(errors[-6:]))

    async def _dump_accessibility(self, device_id: str) -> str:
        code, out, err = await self._adb.run(
            "shell", "cmd", "accessibility", "dump", device_id=device_id, timeout=30.0
        )
        if code == 0 and out.strip():
            return out
        raise RuntimeError(f"accessibility dump: {err or 'empty'}")

    async def _dump_uiautomator_file(self, device_id: str) -> str:
        remote = "/sdcard/droidlens_window_dump.xml"
        code, _, err = await self._adb.run(
            "shell", "uiautomator", "dump", remote, device_id=device_id, timeout=45.0
        )
        if code != 0:
            raise RuntimeError(f"uiautomator dump: {err}")
        _, xml, _ = await self._adb.run("shell", "cat", remote, device_id=device_id, timeout=15.0)
        await self._adb.run("shell", "rm", "-f", remote, device_id=device_id, timeout=5.0)
        if not xml.strip():
            raise RuntimeError("empty dump file")
        return xml

    async def _dump_uiautomator_tty(self, device_id: str) -> str:
        code, out, err = await self._adb.run(
            "exec-out", "uiautomator", "dump", "/dev/tty", device_id=device_id, timeout=45.0
        )
        if code == 0 and out.strip():
            return out
        raise RuntimeError(f"uiautomator tty: {err}")

    async def screenshot(self, device_id: str) -> bytes:
        return await self._adb.screencap_png(device_id)

    async def launch_app(self, device_id: str, package: str, activity: Optional[str] = None) -> None:
        if activity:
            component = activity if "/" in activity else f"{package}/{activity}"
            code, _, err = await self._adb.run(
                "shell", "am", "start", "-n", component, device_id=device_id, timeout=15.0
            )
        else:
            code, _, err = await self._adb.run(
                "shell", "monkey", "-p", package,
                "-c", "android.intent.category.LAUNCHER", "1",
                device_id=device_id, timeout=20.0,
            )
        if code != 0:
            raise RuntimeError(f"Launch failed: {err}")

    async def get_screen_size(self, device_id: str) -> tuple[int, int]:
        _, out, _ = await self._adb.run("shell", "wm", "size", device_id=device_id, timeout=5.0)
        for pattern in [r"Physical size:\s*(\d+)x(\d+)", r"Override size:\s*(\d+)x(\d+)", r"(\d+)x(\d+)"]:
            m = re.search(pattern, out)
            if m:
                return int(m.group(1)), int(m.group(2))
        return 1080, 1920

    def parse_ui_dump(self, raw: str) -> ElementNode:
        tree, _ = self._parser.parse(raw)
        return tree

    def parse_with_rotation(self, raw: str) -> tuple[ElementNode, int]:
        return self._parser.parse(raw)

    @staticmethod
    def screenshot_base64(data: bytes) -> str:
        return base64.b64encode(data).decode("ascii")

    def get_adb(self) -> AdbManager:
        return self._adb
