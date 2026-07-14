"""Central auth, pricing, and payment configuration (env-overridable)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class AuthConfig:
    lifetime_price_inr: int = 199
    currency: str = "INR"
    payment_provider: str = "mock"
    trial_days: int = 7
    access_token_minutes: int = 60
    refresh_token_days: int = 30
    refresh_token_days_remember: int = 90
    admin_emails: tuple[str, ...] = ()


@lru_cache
def get_auth_config() -> AuthConfig:
    admin_raw = os.environ.get("DROIDLENS_ADMIN_EMAIL", "admin@droidlens.local")
    admin_emails = tuple(e.strip().lower() for e in admin_raw.split(",") if e.strip())
    return AuthConfig(
        lifetime_price_inr=int(os.environ.get("DROIDLENS_LIFETIME_PRICE_INR", "199")),
        currency=os.environ.get("DROIDLENS_CURRENCY", "INR"),
        payment_provider=os.environ.get("DROIDLENS_PAYMENT_PROVIDER", "mock"),
        trial_days=int(os.environ.get("DROIDLENS_TRIAL_DAYS", "7")),
        access_token_minutes=int(os.environ.get("DROIDLENS_ACCESS_TOKEN_MINUTES", "60")),
        refresh_token_days=int(os.environ.get("DROIDLENS_REFRESH_TOKEN_DAYS", "30")),
        refresh_token_days_remember=int(os.environ.get("DROIDLENS_REFRESH_TOKEN_DAYS_REMEMBER", "90")),
        admin_emails=admin_emails,
    )
