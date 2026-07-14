"""Shared license computation for auth repositories."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from inspectiq.auth.models import LicenseInfo, LicenseStatus
from inspectiq.auth.plans import get_plan


def _parse_dt(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace('Z', '+00:00'))
    return None


def compute_license(
    plan_id: str,
    status: str,
    trial_started_at: Any = None,
    trial_expires_at: Any = None,
    license_activated_at: Any = None,
) -> LicenseInfo:
    now = datetime.now(timezone.utc)
    plan = get_plan(plan_id) or get_plan('trial')
    plan_name = plan.name if plan else plan_id
    price_inr = plan.price_inr if plan else None
    trial_start = _parse_dt(trial_started_at)
    trial_end = _parse_dt(trial_expires_at)
    activated = _parse_dt(license_activated_at)

    if status == LicenseStatus.LIFETIME.value:
        return LicenseInfo(
            status=LicenseStatus.LIFETIME,
            plan_id=plan_id,
            plan_name=plan_name,
            trial_started_at=trial_start,
            trial_expires_at=trial_end,
            license_activated_at=activated,
            license_expires_at=None,
            days_remaining=None,
            has_premium=True,
            price_inr=price_inr,
        )

    if trial_end:
        exp = trial_end if trial_end.tzinfo else trial_end.replace(tzinfo=timezone.utc)
        days_left = max(0, (exp.date() - now.date()).days)
        if now < exp and status == LicenseStatus.TRIAL_ACTIVE.value:
            return LicenseInfo(
                status=LicenseStatus.TRIAL_ACTIVE,
                plan_id='trial',
                plan_name='Free Trial',
                trial_started_at=trial_start,
                trial_expires_at=trial_end,
                days_remaining=days_left,
                has_premium=True,
                price_inr=None,
            )
        return LicenseInfo(
            status=LicenseStatus.TRIAL_EXPIRED,
            plan_id='trial',
            plan_name='Free Trial (Expired)',
            trial_started_at=trial_start,
            trial_expires_at=trial_end,
            days_remaining=0,
            has_premium=False,
            price_inr=None,
        )

    return LicenseInfo(
        status=LicenseStatus.TRIAL_EXPIRED,
        plan_id=plan_id,
        plan_name=plan_name,
        has_premium=False,
    )
