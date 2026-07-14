"""Shared payment ID generation and license overlay helpers."""

from __future__ import annotations

import secrets
from typing import Any, Optional

from inspectiq.auth.models import LicenseInfo, LicenseStatus


def new_order_id() -> str:
    return f"ORD-{secrets.token_hex(4).upper()}"


def new_transaction_id() -> str:
    return f"TXN-{secrets.token_hex(6).upper()}"


def overlay_pending_payment(info: LicenseInfo, pending: Optional[dict[str, Any]]) -> LicenseInfo:
    if not pending or info.status == LicenseStatus.LIFETIME:
        return info
    payment_id = pending.get("id") or pending.get("payment_id")
    if info.has_premium and info.status == LicenseStatus.TRIAL_ACTIVE:
        return info.model_copy(update={"pending_payment_id": payment_id})
    return info.model_copy(update={
        "status": LicenseStatus.PAYMENT_PENDING,
        "plan_name": "Payment Pending",
        "has_premium": False,
        "pending_payment_id": payment_id,
    })
