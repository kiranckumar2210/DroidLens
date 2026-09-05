"""iOS platform adapter — Simulator (simctl + WDA) and physical devices."""

from __future__ import annotations

import asyncio
import json
import re
import uuid
from typing import Optional

from inspectiq.adapters.base import PlatformAdapter
from inspectiq.adapters.wda_client import WDAClient
from inspectiq.domain.models import DeviceInfo, ElementNode, Platform
from inspectiq.engine.ios_parser import IOSXmlParser

_SIMULATOR_UDID_RE = re.compile(
    r"^[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}$"
)


class IOSAdapter(PlatformAdapter):
    """iOS adapter using simctl, WebDriverAgent, and idevice tools when available."""

    platform = Platform.IOS

    def __init__(self):
        self._parser = IOSXmlParser()
        self._wda = WDAClient()
        self._screen_sizes: dict[str, tuple[int, int]] = {}

    @staticmethod
    def is_simulator(device_id: str) -> bool:
        return bool(_SIMULATOR_UDID_RE.match(device_id))

    async def _run_text(self, *args: str) -> tuple[int, str, str]:
        try:
            proc = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except FileNotFoundError:
            return 127, "", "command not found"
        stdout, stderr = await proc.communicate()
        return (
            proc.returncode or 0,
            stdout.decode("utf-8", errors="replace"),
            stderr.decode("utf-8", errors="replace"),
        )

    async def _run_bytes(self, *args: str) -> tuple[int, bytes, str]:
        try:
            proc = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except FileNotFoundError:
            return 127, b"", "command not found"
        stdout, stderr = await proc.communicate()
        return proc.returncode or 0, stdout, stderr.decode("utf-8", errors="replace")

    async def list_devices(self) -> list[DeviceInfo]:
        devices: list[DeviceInfo] = []

        code, out, _ = await self._run_text("xcrun", "simctl", "list", "devices", "available", "-j")
        if code == 0:
            try:
                data = json.loads(out)
                for runtime, devs in data.get("devices", {}).items():
                    for d in devs:
                        if d.get("isAvailable"):
                            devices.append(
                                DeviceInfo(
                                    id=d["udid"],
                                    platform=Platform.IOS,
                                    name=d.get("name", "Simulator"),
                                    model=d.get("deviceTypeIdentifier"),
                                    os_version=runtime.split(".")[-1] if runtime else None,
                                )
                            )
            except json.JSONDecodeError:
                pass

        code, out, _ = await self._run_text("idevice_id", "-l")
        if code == 0:
            for udid in out.strip().splitlines():
                udid = udid.strip()
                if udid:
                    devices.append(
                        DeviceInfo(
                            id=udid,
                            platform=Platform.IOS,
                            name=f"iOS Device ({udid[:8]}…)",
                        )
                    )
        return devices

    async def connect(self, device_id: str) -> None:
        if self.is_simulator(device_id):
            code, out, _ = await self._run_text("xcrun", "simctl", "list", "devices", "booted", "-j")
            booted = set()
            if code == 0:
                try:
                    data = json.loads(out)
                    for devs in data.get("devices", {}).values():
                        for d in devs:
                            if d.get("state") == "Booted":
                                booted.add(d["udid"])
                except json.JSONDecodeError:
                    pass
            if device_id not in booted:
                boot_code, _, boot_err = await self._run_text("xcrun", "simctl", "boot", device_id)
                if boot_code != 0 and "Unable to boot device in current state: Booted" not in boot_err:
                    raise ConnectionError(f"Cannot boot iOS Simulator: {boot_err}")
            return

        code, _, err = await self._run_text("ideviceinfo", "-u", device_id, "-k", "DeviceName")
        if code != 0:
            raise ConnectionError(
                f"Cannot reach iOS device '{device_id}'. Install libimobiledevice or use Simulator. {err}"
            )

    async def dump_ui(self, device_id: str) -> str:
        if await self._wda.is_available():
            try:
                return await self._wda.get_source()
            except Exception:
                pass

        if self.is_simulator(device_id):
            raise RuntimeError(
                "iOS Simulator UI dump requires WebDriverAgent. "
                "Start WDA (e.g. Appium or xcodebuild test) and set DROIDLENS_WDA_URL if not on :8100."
            )

        code, out, err = await self._run_text("idevice_ui", "-u", device_id, "dump")
        if code == 0 and out.strip():
            return out
        raise RuntimeError(
            "iOS UI dump requires WebDriverAgent or idevice_ui. "
            f"Error: {err or 'no output'}"
        )

    async def screenshot(self, device_id: str) -> bytes:
        if await self._wda.is_available():
            try:
                return await self._wda.get_screenshot()
            except Exception:
                pass

        if self.is_simulator(device_id):
            code, data, err = await self._run_bytes(
                "xcrun", "simctl", "io", device_id, "screenshot", "-"
            )
            if code == 0 and data:
                return data
            raise RuntimeError(f"iOS Simulator screenshot failed: {err}")

        remote = f"/tmp/droidlens_{uuid.uuid4().hex[:8]}.png"
        code, _, err = await self._run_text("idevicescreenshot", "-u", device_id, remote)
        if code != 0:
            raise RuntimeError(f"iOS device screenshot failed: {err}")
        try:
            return open(remote, "rb").read()
        finally:
            try:
                import os
                os.unlink(remote)
            except OSError:
                pass

    async def launch_app(self, device_id: str, package: str, activity: Optional[str] = None) -> None:
        if self.is_simulator(device_id):
            await self._run_text("xcrun", "simctl", "launch", device_id, package)
            return
        raise RuntimeError("Launch app on physical iOS requires WebDriverAgent / Appium session")

    async def get_screen_size(self, device_id: str) -> tuple[int, int]:
        cached = self._screen_sizes.get(device_id)
        if cached:
            return cached

        if self.is_simulator(device_id):
            code, out, _ = await self._run_text("xcrun", "simctl", "io", device_id, "info")
            if code == 0:
                match = re.search(r"Bounds:\s*\{\{(\d+),\s*(\d+)\},\s*\{(\d+),\s*(\d+)\}\}", out)
                if match:
                    w, h = int(match.group(3)), int(match.group(4))
                    self._screen_sizes[device_id] = (w, h)
                    return w, h

        return 390, 844

    def parse_ui_dump(self, raw: str) -> ElementNode:
        return self._parser.parse(raw)
