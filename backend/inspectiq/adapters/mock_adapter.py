"""Mock adapter for development and testing without real devices."""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Optional

from inspectiq.adapters.base import PlatformAdapter
from inspectiq.domain.models import DeviceInfo, ElementNode, Platform

MOCK_ANDROID_XML = """<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
<hierarchy rotation="0">
  <node index="0" text="" resource-id="" class="android.widget.FrameLayout"
        package="com.demo.shop" content-desc="" checkable="false" checked="false"
        clickable="false" enabled="true" focusable="false" focused="false"
        scrollable="false" long-clickable="false" password="false" selected="false"
        bounds="[0,0][1080,1920]">
    <node index="0" text="" resource-id="com.demo.shop:id/login_container"
          class="android.widget.LinearLayout" package="com.demo.shop"
          content-desc="" clickable="false" enabled="true" bounds="[0,200][1080,1700]">
      <node index="0" text="Welcome Back" resource-id="com.demo.shop:id/title"
            class="android.widget.TextView" package="com.demo.shop"
            content-desc="" clickable="false" enabled="true" bounds="[120,250][960,320]"/>
      <node index="1" text="" resource-id="com.demo.shop:id/username_field"
            class="android.widget.EditText" package="com.demo.shop"
            content-desc="Username input" clickable="true" enabled="true"
            bounds="[120,380][960,480]"/>
      <node index="2" text="" resource-id="com.demo.shop:id/password_field"
            class="android.widget.EditText" package="com.demo.shop"
            content-desc="Password input" clickable="true" enabled="true"
            bounds="[120,520][960,620]"/>
      <node index="3" text="Login" resource-id="com.demo.shop:id/loginBtn"
            class="android.widget.Button" package="com.demo.shop"
            content-desc="login" clickable="true" enabled="true"
            bounds="[120,700][960,800]"/>
      <node index="4" text="Submit" resource-id=""
            class="android.widget.TextView" package="com.demo.shop"
            content-desc="" clickable="true" enabled="true"
            bounds="[400,900][680,960]"/>
    </node>
  </node>
</hierarchy>"""

MOCK_IOS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<XCUIElementTypeApplication name="ShopApp" label="ShopApp" type="XCUIElementTypeApplication"
  x="0" y="0" width="390" height="844" enabled="true" visible="true">
  <XCUIElementTypeOther x="0" y="0" width="390" height="844">
    <XCUIElementTypeTextField name="username" label="Username" x="20" y="200" width="350" height="44"/>
    <XCUIElementTypeSecureTextField name="password" label="Password" x="20" y="260" width="350" height="44"/>
    <XCUIElementTypeButton name="login" label="Login" x="20" y="340" width="350" height="50"/>
  </XCUIElementTypeOther>
</XCUIElementTypeApplication>"""


class MockAdapter(PlatformAdapter):
    """Provides realistic mock data for all platforms."""

    def __init__(self, platform: Platform = Platform.ANDROID):
        self.platform = platform
        self._connected_device: Optional[str] = None

    async def list_devices(self) -> list[DeviceInfo]:
        return [
            DeviceInfo(
                id=f"mock-{self.platform.value}-001",
                platform=self.platform,
                name=f"Mock {self.platform.value.title()} Device",
                model="Mock Emulator",
                os_version="14.0" if self.platform == Platform.ANDROID else "17.0",
            )
        ]

    async def connect(self, device_id: str) -> None:
        self._connected_device = device_id

    async def dump_ui(self, device_id: str) -> str:
        if self.platform == Platform.IOS:
            return MOCK_IOS_XML
        if self.platform == Platform.HARMONYOS:
            return MOCK_ANDROID_XML.replace("com.demo.shop", "com.demo.harmony")
        return MOCK_ANDROID_XML

    async def screenshot(self, device_id: str) -> bytes:
        try:
            from PIL import Image, ImageDraw, ImageFont
            import io

            w, h = (1080, 1920) if self.platform != Platform.IOS else (390, 844)
            img = Image.new("RGB", (w, h), color=(18, 22, 28))
            draw = ImageDraw.Draw(img)
            draw.rectangle([0, 0, w, 80], fill=(33, 38, 45))
            draw.text((20, 28), f"DroidLens Mock — {self.platform.value.title()}", fill=(230, 237, 243))
            draw.rectangle([120, 380, 960 if w > 400 else 370, 480 if w > 400 else 244], outline=(88, 166, 255), width=2)
            draw.text((130, 400 if w > 400 else 210), "Username", fill=(139, 148, 158))
            draw.rectangle([120, 520 if w > 400 else 260, 960 if w > 400 else 370, 620 if w > 400 else 304], outline=(88, 166, 255), width=2)
            draw.text((130, 540 if w > 400 else 270), "Password", fill=(139, 148, 158))
            draw.rectangle([120, 700 if w > 400 else 340, 960 if w > 400 else 370, 800 if w > 400 else 390], fill=(35, 134, 54))
            draw.text((480 if w > 400 else 165, 730 if w > 400 else 355), "Login", fill=(255, 255, 255), anchor="mm")
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            return buf.getvalue()
        except ImportError:
            minimal_png = base64.b64decode(
                "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
            )
            return minimal_png

    async def launch_app(self, device_id: str, package: str, activity: Optional[str] = None) -> None:
        pass

    async def get_screen_size(self, device_id: str) -> tuple[int, int]:
        if self.platform == Platform.IOS:
            return 390, 844
        return 1080, 1920

    def parse_ui_dump(self, raw: str) -> ElementNode:
        if self.platform == Platform.IOS:
            from inspectiq.adapters.ios_adapter import IOSAdapter
            return IOSAdapter().parse_ui_dump(raw)
        if self.platform == Platform.HARMONYOS:
            from inspectiq.adapters.harmony_adapter import HarmonyAdapter
            return HarmonyAdapter().parse_ui_dump(raw)
        from inspectiq.engine.xml_parser import AndroidXmlParser
        tree, _ = AndroidXmlParser().parse(raw)
        return tree
