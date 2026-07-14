"""ADB detection, server control, and device communication."""

from __future__ import annotations

import asyncio
import logging
import os
import re
import shutil
from typing import Dict, List, Optional, Tuple

from inspectiq.domain.models import AdbStatus, DeviceInfo, Platform

DEFAULT_TIMEOUT = 30.0
SCREENSHOT_TIMEOUT = 15.0

logger = logging.getLogger(__name__)


class AdbError(Exception):
    pass


class AdbManager:
    """Central ADB wrapper with timeouts and diagnostics."""

    def __init__(self, adb_path: Optional[str] = None):
        self._adb_path = adb_path or os.environ.get("DROIDLENS_ADB") or os.environ.get("INSPECTIQ_ADB")
        self._resolved_path: Optional[str] = None
        self._display_id_cache: Dict[str, str] = {}

    @property
    def adb_path(self) -> str:
        if self._resolved_path:
            return self._resolved_path
        if self._adb_path and shutil.which(self._adb_path):
            self._resolved_path = self._adb_path
            return self._resolved_path
        android_home = os.environ.get("ANDROID_HOME") or os.environ.get("ANDROID_SDK_ROOT")
        if android_home:
            candidate = os.path.join(android_home, "platform-tools", "adb")
            if os.path.isfile(candidate):
                self._resolved_path = candidate
                return self._resolved_path
        found = shutil.which("adb")
        if not found:
            raise AdbError("ADB not found. Install Android platform-tools or set DROIDLENS_ADB.")
        self._resolved_path = found
        return self._resolved_path

    async def run(
        self,
        *args: str,
        device_id: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> Tuple[int, str, str]:
        cmd = [self.adb_path]
        if device_id:
            cmd.extend(["-s", device_id])
        cmd.extend(args)
        try:
            proc = await asyncio.wait_for(
                asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                ),
                timeout=timeout,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            return proc.returncode or 0, stdout.decode("utf-8", errors="replace"), stderr.decode("utf-8", errors="replace")
        except asyncio.TimeoutError:
            raise AdbError(f"ADB command timed out after {timeout}s: {' '.join(cmd)}")

    async def get_status(self) -> AdbStatus:
        try:
            path = self.adb_path
        except AdbError:
            return AdbStatus(installed=False)

        code, out, _ = await self.run("version", timeout=5.0)
        version = out.strip().split("\n")[0] if code == 0 else None

        _, devices_out, _ = await self.run("devices", "-l", timeout=10.0)
        device_count = unauthorized = offline = 0
        for line in devices_out.strip().splitlines()[1:]:
            if not line.strip():
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            state = parts[1]
            if state == "device":
                device_count += 1
            elif state == "unauthorized":
                unauthorized += 1
            elif state == "offline":
                offline += 1

        return AdbStatus(
            installed=True,
            path=path,
            version=version,
            server_running=True,
            device_count=device_count,
            unauthorized_count=unauthorized,
            offline_count=offline,
        )

    async def kill_server(self) -> None:
        await self.run("kill-server", timeout=10.0)

    async def start_server(self) -> None:
        await self.run("start-server", timeout=15.0)

    async def restart_server(self) -> None:
        await self.kill_server()
        await self.start_server()

    async def connect_wifi(self, host: str, port: int = 5555) -> str:
        target = f"{host}:{port}" if ":" not in host else host
        code, out, err = await self.run("connect", target, timeout=15.0)
        msg = (out or err).strip()
        if code != 0 and "connected" not in msg.lower():
            raise AdbError(f"WiFi connect failed: {msg}")
        return msg

    async def disconnect_wifi(self, host: Optional[str] = None) -> str:
        if host:
            code, out, err = await self.run("disconnect", host, timeout=10.0)
        else:
            code, out, err = await self.run("disconnect", timeout=10.0)
        return (out or err).strip()

    async def shell_prop(self, device_id: str, prop: str) -> str:
        _, out, _ = await self.run("shell", "getprop", prop, device_id=device_id, timeout=5.0)
        return out.strip()

    async def get_device_state(self, serial: str) -> Optional[str]:
        """Return adb state for serial: device, unauthorized, offline, or None if absent."""
        try:
            _, out, _ = await self.run("devices", "-l", timeout=10.0)
        except AdbError:
            return None
        for line in out.strip().splitlines()[1:]:
            parts = line.split()
            if len(parts) >= 2 and parts[0] == serial:
                return parts[1]
        return None

    async def list_devices_detailed(self) -> List[DeviceInfo]:
        try:
            _, out, _ = await self.run("devices", "-l", timeout=10.0)
        except AdbError:
            return []

        devices: List[DeviceInfo] = []
        for line in out.strip().splitlines()[1:]:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            serial = parts[0]
            state = parts[1]
            if state != "device":
                continue

            model = manufacturer = "Unknown"
            for p in parts[2:]:
                if p.startswith("model:"):
                    model = p.split(":", 1)[1].replace("_", " ")
                if p.startswith("device:"):
                    manufacturer = p.split(":", 1)[1]

            os_version = await self.shell_prop(serial, "ro.build.version.release")
            sdk = await self.shell_prop(serial, "ro.build.version.sdk")
            brand = await self.shell_prop(serial, "ro.product.manufacturer") or manufacturer
            product = await self.shell_prop(serial, "ro.product.model") or model

            _, size_out, _ = await self.run("shell", "wm", "size", device_id=serial, timeout=5.0)
            resolution = None
            m = re.search(r"(\d+x\d+)", size_out)
            if m:
                resolution = m.group(1)

            _, orient_out, _ = await self.run("shell", "dumpsys", "input", device_id=serial, timeout=8.0)
            orientation = "portrait"
            if "SurfaceOrientation: 1" in orient_out or "SurfaceOrientation: 3" in orient_out:
                orientation = "landscape"

            battery_level = None
            _, bat_out, _ = await self.run("shell", "dumpsys", "battery", device_id=serial, timeout=5.0)
            bm = re.search(r"level:\s*(\d+)", bat_out)
            if bm:
                battery_level = int(bm.group(1))

            connection_type = "wifi" if ":" in serial else "usb"
            is_emulator = serial.startswith("emulator-") or await self.shell_prop(serial, "ro.kernel.qemu") == "1"

            devices.append(
                DeviceInfo(
                    id=serial,
                    serial=serial,
                    platform=Platform.ANDROID,
                    name=f"{product} ({serial})",
                    model=product,
                    manufacturer=brand,
                    os_version=os_version or None,
                    sdk_version=sdk or None,
                    status=state,
                    connection_type=connection_type,
                    resolution=resolution,
                    orientation=orientation,
                    battery_level=battery_level,
                    is_emulator=is_emulator,
                )
            )
        return devices

    async def list_packages(self, device_id: str, filter_text: str = "") -> List[str]:
        _, out, _ = await self.run("shell", "pm", "list", "packages", device_id=device_id, timeout=30.0)
        packages = []
        for line in out.splitlines():
            if line.startswith("package:"):
                pkg = line.replace("package:", "").strip()
                if not filter_text or filter_text.lower() in pkg.lower():
                    packages.append(pkg)
        return sorted(packages)

    async def get_primary_display_id(self, device_id: str) -> Optional[str]:
        """Resolve SurfaceFlinger display ID for the active primary screen (multi-display devices)."""
        if device_id in self._display_id_cache:
            return self._display_id_cache[device_id]

        display_id: Optional[str] = None

        # Prefer the active viewport from DisplayManager (accurate on foldables/multi-display)
        _, out, _ = await self.run("shell", "dumpsys", "display", device_id=device_id, timeout=10.0)
        active = re.search(
            r"isActive=true[^}]*uniqueId='local:(\d+)'",
            out,
        )
        if active:
            display_id = active.group(1)
        else:
            # Fallback: first ON display block with uniqueId
            on_block = re.search(
                r"Display Id=\d+\s*\n\s*Display State=ON[\s\S]*?uniqueId='local:(\d+)'",
                out,
            )
            if on_block:
                display_id = on_block.group(1)

        if not display_id:
            _, sf_out, _ = await self.run(
                "shell", "dumpsys", "SurfaceFlinger", "--display-id",
                device_id=device_id, timeout=10.0,
            )
            sf_match = re.search(r"Display (\d+) \(HWC display 0\)", sf_out)
            if sf_match:
                display_id = sf_match.group(1)
            else:
                first = re.search(r"Display (\d+) \(HWC", sf_out)
                if first:
                    display_id = first.group(1)

        if display_id:
            self._display_id_cache[device_id] = display_id
        return display_id

    async def screencap_png(self, device_id: str) -> bytes:
        """Capture device screenshot as PNG with multiple fallback strategies."""
        display_id = await self.get_primary_display_id(device_id)
        if display_id:
            logger.info("Using display ID %s for screencap on %s", display_id, device_id)
        strategies = (
            self._screencap_exec_out,
            self._screencap_via_file,
        )
        errors: List[str] = []
        for strategy in strategies:
            name = strategy.__name__
            try:
                raw = await strategy(device_id, display_id)
                png = self._normalize_png(raw)
                if png.startswith(b"\x89PNG") and len(png) > 24:
                    return png
                errors.append(f"{name}: invalid PNG header ({len(raw)} bytes)")
            except AdbError as exc:
                errors.append(f"{name}: {exc}")
            except asyncio.TimeoutError:
                errors.append(f"{name}: timed out")
            except Exception as exc:
                errors.append(f"{name}: {exc}")
        raise AdbError("Screenshot capture failed. " + "; ".join(errors))

    async def _screencap_exec_out(self, device_id: str, display_id: Optional[str]) -> bytes:
        cmd = [self.adb_path, "-s", device_id, "exec-out", "screencap"]
        if display_id:
            cmd.extend(["-d", display_id])
        cmd.extend(["-p"])
        proc = await asyncio.wait_for(
            asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            ),
            timeout=SCREENSHOT_TIMEOUT,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=SCREENSHOT_TIMEOUT)
        if proc.returncode != 0:
            raise AdbError(f"exec-out screencap failed: {stderr.decode(errors='replace')}")
        if not stdout:
            raise AdbError("exec-out screencap returned empty data")
        return stdout

    async def _screencap_via_file(self, device_id: str, display_id: Optional[str]) -> bytes:
        """Write PNG on device then read via exec-out cat — avoids pipe CRLF corruption."""
        remote = "/sdcard/droidlens_screencap.png"
        shell_args = ["shell", "screencap"]
        if display_id:
            shell_args.extend(["-d", display_id])
        shell_args.extend(["-p", remote])
        code, _, err = await self.run(*shell_args, device_id=device_id, timeout=SCREENSHOT_TIMEOUT)
        if code != 0:
            raise AdbError(f"screencap to file failed: {err}")

        proc = await asyncio.wait_for(
            asyncio.create_subprocess_exec(
                self.adb_path, "-s", device_id, "exec-out", "cat", remote,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            ),
            timeout=SCREENSHOT_TIMEOUT,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=SCREENSHOT_TIMEOUT)
        await self.run("shell", "rm", "-f", remote, device_id=device_id, timeout=5.0)
        if proc.returncode != 0:
            raise AdbError(f"cat screenshot failed: {stderr.decode(errors='replace')}")
        if not stdout:
            raise AdbError("cat screenshot returned empty data")
        return stdout

    @staticmethod
    def _normalize_png(data: bytes) -> bytes:
        """Fix common Android ADB PNG transport issues (CRLF corruption, leading junk)."""
        if not data:
            return data
        if data.startswith(b"\x89PNG"):
            return data
        # Classic bug: adb converts 0x0A to 0x0D 0x0A inside PNG stream
        fixed = data.replace(b"\r\n", b"\n")
        if fixed.startswith(b"\x89PNG"):
            return fixed
        for blob in (data, fixed):
            idx = blob.find(b"\x89PNG")
            if idx >= 0:
                return blob[idx:]
        return data

    @staticmethod
    def png_dimensions(data: bytes) -> Tuple[int, int]:
        if len(data) < 24:
            return 0, 0
        import struct
        w, h = struct.unpack(">II", data[16:24])
        return w, h
