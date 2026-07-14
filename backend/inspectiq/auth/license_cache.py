"""Signed license cache for offline grace-period validation."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from typing import Any, Optional

from inspectiq.auth.models import LicenseInfo

_CACHE_SECRET = os.environ.get(
    "DROIDLENS_LICENSE_CACHE_SECRET",
    os.environ.get("DROIDLENS_JWT_SECRET", "droidlens-dev-license-cache-secret"),
)
_CACHE_TTL_SECONDS = int(os.environ.get("DROIDLENS_LICENSE_CACHE_TTL", str(7 * 86400)))


def sign_license_cache(user_id: str, license_info: LicenseInfo) -> str:
    payload = {
        "user_id": user_id,
        "license": license_info.model_dump(mode="json"),
        "exp": int(time.time()) + _CACHE_TTL_SECONDS,
    }
    body = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    sig = hmac.new(_CACHE_SECRET.encode(), body.encode(), hashlib.sha256).hexdigest()
    return f"{body}.{sig}"


def verify_license_cache(token: str, user_id: str) -> Optional[dict[str, Any]]:
    try:
        body, sig = token.rsplit(".", 1)
        expected = hmac.new(_CACHE_SECRET.encode(), body.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return None
        payload = json.loads(body)
        if payload.get("user_id") != user_id:
            return None
        if payload.get("exp", 0) < time.time():
            return None
        return payload.get("license")
    except (ValueError, json.JSONDecodeError):
        return None
