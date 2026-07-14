"""Resolve configured payment provider implementation."""

from __future__ import annotations

from typing import Any

from inspectiq.auth.config import get_auth_config
from inspectiq.auth.providers.base import PaymentProvider
from inspectiq.auth.providers.mock import MockPaymentProvider
from inspectiq.auth.providers.phonepe import PhonePePaymentProvider

_PROVIDERS = {
    "mock": MockPaymentProvider,
    "phonepe": PhonePePaymentProvider,
}


def get_payment_provider(repo: Any) -> PaymentProvider:
    cfg = get_auth_config()
    cls = _PROVIDERS.get(cfg.payment_provider)
    if not cls:
        raise ValueError(f"Unknown payment provider: {cfg.payment_provider}")
    return cls(repo)
