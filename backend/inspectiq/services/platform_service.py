"""Platform toolchain status — ADB, simctl, HDC, WDA, cloud Appium."""

from __future__ import annotations

import asyncio
import shutil
from typing import Any

from inspectiq.adapters.cloud_adapter import CloudAppiumAdapter
from inspectiq.adapters.wda_client import WDAClient
from inspectiq.domain.models import Platform
from inspectiq.services.device_service import DeviceService


class PlatformService:
    def __init__(self, devices_svc: DeviceService):
        self._devices = devices_svc
        self._wda = WDAClient()
        self._cloud = CloudAppiumAdapter()

    async def _cmd_exists(self, name: str) -> bool:
        return shutil.which(name) is not None

    async def _run_check(self, *args: str) -> bool:
        try:
            proc = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await proc.wait()
            return proc.returncode == 0
        except FileNotFoundError:
            return False

    async def get_status(self) -> dict[str, Any]:
        adb = await self._devices.adb_status()
        xcrun = await self._cmd_exists("xcrun")
        simctl_ok = xcrun and await self._run_check("xcrun", "simctl", "list")
        idevice = await self._cmd_exists("idevice_id")
        hdc = await self._cmd_exists("hdc")
        wda = await self._wda.is_available()
        cloud = self._cloud.is_configured()

        ios_devices = 0
        harmony_devices = 0
        if simctl_ok or idevice:
            from inspectiq.adapters.ios_adapter import IOSAdapter
            ios_devices = len(await IOSAdapter().list_devices())
        if hdc:
            from inspectiq.adapters.harmony_adapter import HarmonyAdapter
            harmony_devices = len(await HarmonyAdapter().list_devices())

        return {
            "platforms": {
                Platform.ANDROID.value: {
                    "available": adb.installed,
                    "device_count": adb.device_count,
                    "tool": "adb",
                },
                Platform.IOS.value: {
                    "available": simctl_ok or idevice or wda,
                    "device_count": ios_devices,
                    "tools": {
                        "simctl": simctl_ok,
                        "idevice": idevice,
                        "wda": wda,
                    },
                },
                Platform.HARMONYOS.value: {
                    "available": hdc,
                    "device_count": harmony_devices,
                    "tool": "hdc",
                },
                "cloud": {
                    "available": cloud,
                    "device_count": 1 if cloud else 0,
                    "tool": "appium",
                },
            },
        }
