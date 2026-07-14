"""Platform adapter interface and factory."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from inspectiq.domain.models import DeviceInfo, ElementNode, Platform


class PlatformAdapter(ABC):
    """Abstract adapter for mobile platform inspection."""

    platform: Platform

    @abstractmethod
    async def list_devices(self) -> list[DeviceInfo]:
        ...

    @abstractmethod
    async def connect(self, device_id: str) -> None:
        ...

    @abstractmethod
    async def dump_ui(self, device_id: str) -> str:
        ...

    @abstractmethod
    async def screenshot(self, device_id: str) -> bytes:
        ...

    @abstractmethod
    async def launch_app(self, device_id: str, package: str, activity: Optional[str] = None) -> None:
        ...

    @abstractmethod
    def parse_ui_dump(self, raw: str) -> ElementNode:
        ...

    @abstractmethod
    async def get_screen_size(self, device_id: str) -> tuple[int, int]:
        ...


def get_adapter(platform: Platform, use_mock: bool = False) -> PlatformAdapter:
    if use_mock:
        from inspectiq.adapters.mock_adapter import MockAdapter

        return MockAdapter(platform)

    if platform == Platform.ANDROID:
        from inspectiq.adapters.android_adapter import AndroidAdapter

        return AndroidAdapter()
    if platform == Platform.IOS:
        from inspectiq.adapters.ios_adapter import IOSAdapter

        return IOSAdapter()
    if platform == Platform.HARMONYOS:
        from inspectiq.adapters.harmony_adapter import HarmonyAdapter

        return HarmonyAdapter()

    raise ValueError(f"Unsupported platform: {platform}")
