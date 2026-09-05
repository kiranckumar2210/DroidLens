"""Remote Appium 2 session adapter for cloud device farms."""

from __future__ import annotations

import base64
import json
import os
import uuid
from typing import Any, Optional

import httpx

from inspectiq.adapters.base import PlatformAdapter
from inspectiq.domain.models import DeviceInfo, ElementNode, Platform
from inspectiq.engine.ios_parser import IOSXmlParser
from inspectiq.engine.xml_parser import AndroidXmlParser


CLOUD_DEVICE_ID = "cloud-appium"


class CloudAppiumAdapter(PlatformAdapter):
    """Connect to BrowserStack, Sauce Labs, or any Appium 2 hub via REST."""

    platform = Platform.ANDROID

    def __init__(self):
        self._base_url = os.environ.get("DROIDLENS_APPIUM_URL", "").rstrip("/")
        caps_raw = os.environ.get("DROIDLENS_APPIUM_CAPABILITIES", "{}")
        try:
            self._capabilities: dict[str, Any] = json.loads(caps_raw)
        except json.JSONDecodeError:
            self._capabilities = {}
        plat = self._capabilities.get("platformName", "Android").lower()
        if plat in ("ios", "iphone", "ipad"):
            self.platform = Platform.IOS
        self._session_id: Optional[str] = None
        self._android_parser = AndroidXmlParser()
        self._ios_parser = IOSXmlParser()

    def is_configured(self) -> bool:
        return bool(self._base_url)

    async def _request(self, method: str, path: str, **kwargs) -> dict:
        if not self._base_url:
            raise RuntimeError(
                "Cloud device farm not configured. Set DROIDLENS_APPIUM_URL and DROIDLENS_APPIUM_CAPABILITIES."
            )
        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.request(method, f"{self._base_url}{path}", **kwargs)
            if r.status_code >= 400:
                detail = r.text[:500]
                raise RuntimeError(f"Appium request failed ({r.status_code}): {detail}")
            return r.json()

    async def list_devices(self) -> list[DeviceInfo]:
        if not self.is_configured():
            return []
        label = self._capabilities.get("deviceName") or "Cloud Appium Session"
        return [
            DeviceInfo(
                id=CLOUD_DEVICE_ID,
                platform=self.platform,
                name=f"Cloud — {label}",
                model=self._capabilities.get("platformName"),
                os_version=self._capabilities.get("platformVersion"),
            )
        ]

    async def connect(self, device_id: str) -> None:
        if device_id != CLOUD_DEVICE_ID:
            raise ConnectionError(f"Unknown cloud device '{device_id}'")
        payload = {
            "capabilities": {
                "alwaysMatch": self._capabilities,
            }
        }
        data = await self._request("POST", "/session", json=payload)
        self._session_id = data.get("value", {}).get("sessionId")
        if not self._session_id:
            raise ConnectionError("Appium session creation did not return sessionId")

    async def dump_ui(self, device_id: str) -> str:
        if not self._session_id:
            await self.connect(device_id)
        data = await self._request("GET", f"/session/{self._session_id}/source")
        raw = data.get("value")
        if not isinstance(raw, str) or not raw.strip():
            raise RuntimeError("Appium page source was empty")
        return raw

    async def screenshot(self, device_id: str) -> bytes:
        if not self._session_id:
            await self.connect(device_id)
        data = await self._request("GET", f"/session/{self._session_id}/screenshot")
        value = data.get("value")
        if not isinstance(value, str) or not value:
            raise RuntimeError("Appium screenshot was empty")
        return base64.b64decode(value)

    async def launch_app(self, device_id: str, package: str, activity: Optional[str] = None) -> None:
        if not self._session_id:
            await self.connect(device_id)
        if self.platform == Platform.IOS:
            await self._request(
                "POST",
                f"/session/{self._session_id}/appium/device/activate_app",
                json={"appId": package},
            )
        else:
            await self._request(
                "POST",
                f"/session/{self._session_id}/appium/device/activate_app",
                json={"appId": package},
            )

    async def get_screen_size(self, device_id: str) -> tuple[int, int]:
        if self.platform == Platform.IOS:
            return 390, 844
        return 1080, 1920

    def parse_ui_dump(self, raw: str) -> ElementNode:
        if self.platform == Platform.IOS or "XCUIElementType" in raw:
            return self._ios_parser.parse(raw)
        tree, _ = self._android_parser.parse(raw)
        return tree

    async def disconnect(self) -> None:
        if self._session_id and self._base_url:
            try:
                await self._request("DELETE", f"/session/{self._session_id}")
            except Exception:
                pass
            self._session_id = None
