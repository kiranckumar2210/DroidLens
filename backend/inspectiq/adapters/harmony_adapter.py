"""HarmonyOS platform adapter using HDC."""

from __future__ import annotations

import asyncio
import uuid
import xml.etree.ElementTree as ET
from typing import Optional

from inspectiq.adapters.base import PlatformAdapter
from inspectiq.domain.models import Bounds, DeviceInfo, ElementNode, Platform


class HarmonyAdapter(PlatformAdapter):
    platform = Platform.HARMONYOS

    async def _run(self, *args: str, device_id: Optional[str] = None) -> tuple[int, str, str]:
        cmd = ["hdc"]
        if device_id:
            cmd.extend(["-t", device_id])
        cmd.extend(args)
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        return proc.returncode or 0, stdout.decode("utf-8", errors="replace"), stderr.decode("utf-8", errors="replace")

    async def list_devices(self) -> list[DeviceInfo]:
        code, out, _ = await self._run("list", "targets")
        if code != 0:
            return []

        devices: list[DeviceInfo] = []
        for line in out.strip().splitlines():
            line = line.strip()
            if not line or line.startswith("[") and "Empty" in line:
                continue
            device_id = line.split()[0] if line.split() else line
            devices.append(
                DeviceInfo(
                    id=device_id,
                    platform=Platform.HARMONYOS,
                    name=f"HarmonyOS ({device_id})",
                )
            )
        return devices

    async def connect(self, device_id: str) -> None:
        code, _, err = await self._run("shell", "echo", "ok", device_id=device_id)
        if code != 0:
            raise ConnectionError(f"Cannot connect to HarmonyOS device: {err}")

    async def dump_ui(self, device_id: str) -> str:
        code, out, err = await self._run(
            "shell", "uitest", "dumpLayout", "-a", device_id=device_id
        )
        if code != 0 or not out.strip():
            raise RuntimeError(
                f"HarmonyOS UI dump failed. Ensure hdc and uitest are available. {err}"
            )
        return out

    async def screenshot(self, device_id: str) -> bytes:
        remote = "/data/local/tmp/droidlens_screen.jpeg"
        await self._run("shell", "snapshot_display", "-f", remote, device_id=device_id)
        proc = await asyncio.create_subprocess_exec(
            "hdc", "-t", device_id, "file", "recv", remote, "/dev/stdout",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(f"HarmonyOS screenshot failed: {stderr.decode()}")
        return stdout

    async def launch_app(self, device_id: str, package: str, activity: Optional[str] = None) -> None:
        await self._run("shell", "aa", "start", "-a", activity or "MainAbility", "-b", package, device_id=device_id)

    async def get_screen_size(self, device_id: str) -> tuple[int, int]:
        return 1260, 2720

    def parse_ui_dump(self, raw: str) -> ElementNode:
        root_el = ET.fromstring(raw)

        def parse_node(el: ET.Element, parent_id: Optional[str] = None) -> ElementNode:
            node_id = str(uuid.uuid4())
            bounds = Bounds.from_string(el.attrib.get("bounds", ""))
            text = el.attrib.get("text") or el.attrib.get("content") or None
            resource_id = el.attrib.get("id") or el.attrib.get("key") or None

            node = ElementNode(
                id=node_id,
                platform=Platform.HARMONYOS,
                class_name=el.tag,
                text=text if text else None,
                resource_id=resource_id,
                accessibility_id=el.attrib.get("accessibility-id") or resource_id,
                content_desc=el.attrib.get("description") or None,
                bounds=bounds,
                enabled=el.attrib.get("enabled", "true") == "true",
                visible=el.attrib.get("visible", "true") == "true",
                clickable=el.attrib.get("clickable", "false") == "true",
                raw_attributes=dict(el.attrib),
                parent_id=parent_id,
            )
            for child_el in el:
                node.children.append(parse_node(child_el, node_id))
            return node

        return parse_node(root_el)
