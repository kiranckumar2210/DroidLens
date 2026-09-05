"""WebDriverAgent HTTP client for iOS simulator / device inspection."""

from __future__ import annotations

import base64
import os
from typing import Optional

import httpx


class WDAClient:
    """Minimal WDA client — page source and screenshots via HTTP."""

    def __init__(self, base_url: Optional[str] = None, timeout: float = 30.0):
        self.base_url = (base_url or os.environ.get("DROIDLENS_WDA_URL", "http://127.0.0.1:8100")).rstrip("/")
        self.timeout = timeout

    async def is_available(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(f"{self.base_url}/status")
                return r.status_code == 200
        except Exception:
            return False

    async def get_source(self) -> str:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.get(f"{self.base_url}/source")
            r.raise_for_status()
            data = r.json()
            value = data.get("value")
            if isinstance(value, str) and value.strip():
                return value
            raise RuntimeError("WDA /source returned empty page source")

    async def get_screenshot(self) -> bytes:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.get(f"{self.base_url}/screenshot")
            r.raise_for_status()
            data = r.json()
            value = data.get("value")
            if not isinstance(value, str) or not value:
                raise RuntimeError("WDA /screenshot returned empty data")
            return base64.b64decode(value)
