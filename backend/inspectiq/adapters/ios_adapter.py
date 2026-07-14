"""iOS platform adapter (XCTest / accessibility hierarchy)."""

from __future__ import annotations

import asyncio
import uuid
import xml.etree.ElementTree as ET
from typing import Optional

from inspectiq.adapters.base import PlatformAdapter
from inspectiq.domain.models import Bounds, DeviceInfo, ElementNode, Platform


class IOSAdapter(PlatformAdapter):
    """iOS adapter using idevice tools / simctl when available."""

    platform = Platform.IOS

    async def _run(self, *args: str) -> tuple[int, str, str]:
        proc = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        return proc.returncode or 0, stdout.decode("utf-8", errors="replace"), stderr.decode("utf-8", errors="replace")

    async def list_devices(self) -> list[DeviceInfo]:
        devices: list[DeviceInfo] = []

        code, out, _ = await self._run("xcrun", "simctl", "list", "devices", "available", "-j")
        if code == 0:
            import json

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

        code, out, _ = await self._run("idevice_id", "-l")
        if code == 0:
            for udid in out.strip().splitlines():
                if udid.strip():
                    devices.append(
                        DeviceInfo(
                            id=udid.strip(),
                            platform=Platform.IOS,
                            name=f"iOS Device ({udid[:8]}...)",
                        )
                    )
        return devices

    async def connect(self, device_id: str) -> None:
        pass

    async def dump_ui(self, device_id: str) -> str:
        code, out, err = await self._run("idevice_ui", "-u", device_id, "dump")
        if code == 0 and out.strip():
            return out
        raise RuntimeError(
            "iOS UI dump requires idevice_ui or WebDriverAgent. "
            f"Use mock mode for development. Error: {err}"
        )

    async def screenshot(self, device_id: str) -> bytes:
        code, out, err = await self._run("xcrun", "simctl", "io", device_id, "screenshot", "-")
        if code == 0 and out:
            return out.encode("latin-1") if isinstance(out, str) else out
        raise RuntimeError(f"iOS screenshot failed: {err}")

    async def launch_app(self, device_id: str, package: str, activity: Optional[str] = None) -> None:
        await self._run("xcrun", "simctl", "launch", device_id, package)

    async def get_screen_size(self, device_id: str) -> tuple[int, int]:
        return 390, 844

    def parse_ui_dump(self, raw: str) -> ElementNode:
        root_el = ET.fromstring(raw)

        def parse_node(el: ET.Element, parent_id: Optional[str] = None) -> ElementNode:
            node_id = str(uuid.uuid4())
            attrs = el.attrib

            x = int(float(attrs.get("x", 0)))
            y = int(float(attrs.get("y", 0)))
            w = int(float(attrs.get("width", 0)))
            h = int(float(attrs.get("height", 0)))
            bounds = Bounds(x1=x, y1=y, x2=x + w, y2=y + h) if w and h else None

            label = attrs.get("label") or None
            name = attrs.get("name") or attrs.get("identifier") or None
            value = attrs.get("value") or None
            type_name = el.tag if el.tag.startswith("XCUI") else attrs.get("type", el.tag)

            node = ElementNode(
                id=node_id,
                platform=Platform.IOS,
                class_name=type_name or "",
                type_name=type_name,
                label=label,
                name=name,
                value=value,
                text=label or value,
                accessibility_id=name,
                bounds=bounds,
                enabled=attrs.get("enabled", "true").lower() == "true",
                visible=attrs.get("visible", "true").lower() == "true",
                clickable=attrs.get("accessible", "false").lower() == "true",
                raw_attributes=dict(attrs),
                parent_id=parent_id,
            )
            for child_el in el:
                node.children.append(parse_node(child_el, node_id))
            return node

        return parse_node(root_el)
