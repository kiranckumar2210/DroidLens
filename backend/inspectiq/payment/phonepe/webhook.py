"""PhonePe webhook verification and event processing."""

from __future__ import annotations

import hashlib
import hmac
from typing import Any, Optional

from inspectiq.logging_config import get_logger
from inspectiq.payment.phonepe.config import PhonePeConfig, get_phonepe_config

logger = get_logger("droidlens.payment.phonepe.webhook")


def compute_webhook_authorization(username: str, password: str) -> str:
    """Expected Authorization header value per PhonePe docs: SHA256(username:password)."""
    digest = hashlib.sha256(f"{username}:{password}".encode()).hexdigest()
    return digest


def verify_webhook_authorization(header: Optional[str], config: Optional[PhonePeConfig] = None) -> bool:
    cfg = config or get_phonepe_config()
    if not cfg.webhook_username or not cfg.webhook_password:
        logger.warning("phonepe_webhook_credentials_missing — rejecting webhook")
        return False
    if not header:
        return False
    expected = compute_webhook_authorization(cfg.webhook_username, cfg.webhook_password)
    token = header.strip()
    if token.upper().startswith("SHA256"):
        token = token.split(" ", 1)[-1].strip()
    return hmac.compare_digest(token, expected)


def parse_webhook_event(payload: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Return (event_name, payload_dict)."""
    event = str(payload.get("event") or "")
    inner = payload.get("payload")
    if isinstance(inner, dict):
        return event, inner
    return event, payload


def webhook_event_id(event: str, inner: dict[str, Any]) -> str:
    """Stable idempotency key for a webhook delivery."""
    order_id = inner.get("orderId") or inner.get("merchantOrderId") or inner.get("refundId") or ""
    state = inner.get("state") or ""
    txn = ""
    details = inner.get("paymentDetails") or []
    if details:
        txn = details[-1].get("transactionId") or ""
    return f"{event}:{order_id}:{state}:{txn}"
