"""Device manager and platform-aware live validation."""

from __future__ import annotations

from typing import List, Optional

from inspectiq.adb.manager import AdbError, AdbManager
from inspectiq.adapters.android_adapter import AndroidAdapter
from inspectiq.adapters.cloud_adapter import CLOUD_DEVICE_ID, CloudAppiumAdapter
from inspectiq.domain.models import AdbStatus, DeviceInfo, Platform


class DeviceService:
    def __init__(self):
        self._adb = AdbManager()
        self._adapter = AndroidAdapter(self._adb)
        self._cloud = CloudAppiumAdapter()

    async def adb_status(self) -> AdbStatus:
        try:
            return await self._adb.get_status()
        except AdbError:
            return AdbStatus(installed=False)

    async def list_android_devices(self) -> List[DeviceInfo]:
        return await self._adapter.list_devices()

    async def refresh_devices(self) -> List[DeviceInfo]:
        try:
            await self._adb.start_server()
        except AdbError:
            pass
        return await self._adapter.list_devices()

    async def restart_adb(self) -> AdbStatus:
        await self._adb.restart_server()
        return await self.adb_status()

    async def kill_adb(self) -> None:
        await self._adb.kill_server()

    async def connect_wifi(self, host: str, port: int = 5555) -> dict:
        msg = await self._adb.connect_wifi(host, port)
        devices = await self.list_android_devices()
        return {"message": msg, "devices": devices}

    async def disconnect_wifi(self, host: Optional[str] = None) -> dict:
        msg = await self._adb.disconnect_wifi(host)
        return {"message": msg}

    async def list_packages(self, device_id: str, filter_text: str = "") -> List[str]:
        return await self._adb.list_packages(device_id, filter_text)

    async def validate_device_for_live(
        self, device_id: str, platform: Platform = Platform.ANDROID
    ) -> None:
        """Raise if device cannot be used for live inspection on the given platform."""
        from inspectiq.services.inspection_service import InspectionService

        if InspectionService.is_mock_device(device_id):
            raise AdbError(
                f"'{device_id}' is a mock device ID. Use Dashboard → Open Mock Project for sample data."
            )

        if device_id == CLOUD_DEVICE_ID:
            if not self._cloud.is_configured():
                raise AdbError(
                    "Cloud Appium not configured. Set DROIDLENS_APPIUM_URL and DROIDLENS_APPIUM_CAPABILITIES."
                )
            return

        if platform == Platform.ANDROID:
            state = await self._adb.get_device_state(device_id)
            if state is None:
                raise AdbError(
                    f"Device '{device_id}' not found. Connect via USB/WiFi and run adb devices."
                )
            if state == "unauthorized":
                raise AdbError(
                    f"Device '{device_id}' is unauthorized. Accept the USB debugging prompt on the device."
                )
            if state == "offline":
                raise AdbError(f"Device '{device_id}' is offline. Reconnect the cable or restart ADB.")
            if state != "device":
                raise AdbError(f"Device '{device_id}' is in state '{state}' — expected 'device'.")
            return

        if platform == Platform.IOS:
            from inspectiq.adapters.ios_adapter import IOSAdapter

            adapter = IOSAdapter()
            known = {d.id for d in await adapter.list_devices()}
            if device_id not in known:
                raise AdbError(
                    f"iOS device '{device_id}' not found. Boot a Simulator or connect a physical device."
                )
            return

        if platform == Platform.HARMONYOS:
            from inspectiq.adapters.harmony_adapter import HarmonyAdapter

            adapter = HarmonyAdapter()
            known = {d.id for d in await adapter.list_devices()}
            if device_id not in known:
                raise AdbError(
                    f"HarmonyOS device '{device_id}' not found. Connect via HDC and run hdc list targets."
                )
            return

        raise AdbError(f"Unsupported platform: {platform.value}")
