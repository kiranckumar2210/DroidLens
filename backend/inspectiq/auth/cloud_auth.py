"""Validate cloud-issued JWTs against a remote DroidLens auth API (desktop hybrid mode)."""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any, Optional

import httpx

from inspectiq.auth.models import AuthUser, LicenseInfo, LicenseStatus

logger = logging.getLogger(__name__)


def cloud_auth_url() -> Optional[str]:
    raw = os.environ.get("DROIDLENS_CLOUD_AUTH_URL", "").strip()
    return raw.rstrip("/") if raw else None


def fetch_cloud_profile(token: str) -> Optional[dict[str, Any]]:
    base = cloud_auth_url()
    if not base:
        return None
    try:
        with httpx.Client(timeout=12.0) as client:
            res = client.get(
                f"{base}/profile",
                headers={"Authorization": f"Bearer {token}"},
            )
            if res.status_code != 200:
                logger.warning("Cloud profile fetch failed: HTTP %s", res.status_code)
                return None
            return res.json()
    except httpx.HTTPError as exc:
        logger.warning("Cloud profile fetch error: %s", exc)
        return None


def _parse_dt(value: Any) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def user_from_cloud_profile(data: dict[str, Any]) -> Optional[AuthUser]:
    user = data.get("user")
    if not isinstance(user, dict):
        return None
    try:
        return AuthUser(
            id=str(user["id"]),
            full_name=str(user.get("full_name", "")),
            email=user["email"],
            created_at=_parse_dt(user.get("created_at")) or datetime.now(),
            avatar_url=user.get("avatar_url"),
            last_login=_parse_dt(user.get("last_login")),
            status=str(user.get("status", "active")),
            role=str(user.get("role", "user")),
        )
    except (KeyError, TypeError, ValueError) as exc:
        logger.warning("Invalid cloud user payload: %s", exc)
        return None


def license_from_cloud_profile(data: dict[str, Any]) -> Optional[LicenseInfo]:
    lic = data.get("license")
    if not isinstance(lic, dict):
        return None
    try:
        status_raw = str(lic.get("status", "guest"))
        try:
            status = LicenseStatus(status_raw)
        except ValueError:
            status = LicenseStatus.GUEST
        return LicenseInfo(
            status=status,
            plan_id=str(lic.get("plan_id", "guest")),
            plan_name=str(lic.get("plan_name", "Guest")),
            trial_started_at=_parse_dt(lic.get("trial_started_at")),
            trial_expires_at=_parse_dt(lic.get("trial_expires_at")),
            license_activated_at=_parse_dt(lic.get("license_activated_at")),
            license_expires_at=_parse_dt(lic.get("license_expires_at")),
            days_remaining=lic.get("days_remaining"),
            has_premium=bool(lic.get("has_premium")),
            license_id=lic.get("license_id"),
        )
    except (TypeError, ValueError) as exc:
        logger.warning("Invalid cloud license payload: %s", exc)
        return None
