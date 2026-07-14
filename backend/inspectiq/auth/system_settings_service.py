"""Singleton system settings service with in-memory cache."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from inspectiq.auth.config import get_auth_config
from inspectiq.auth.system_settings_models import (
    FeatureFlags,
    PaymentSettings,
    SubscriptionSettings,
    SystemConfigPublic,
    SystemSettings,
    SystemSettingsUpdate,
)

_repo: Any = None
_cache: Optional[SystemSettings] = None


def _get_repo():
    global _repo
    if _repo is None:
        from inspectiq.auth.repository import create_auth_repository
        _repo = create_auth_repository()
    return _repo


def configure_system_settings_repo(repo: Any) -> None:
    """Replace persistence target — used by unit tests."""
    global _repo, _cache
    _repo = repo
    _cache = None


def _default_settings() -> SystemSettings:
    cfg = get_auth_config()
    return SystemSettings(
        subscription=SubscriptionSettings(),
        payment=PaymentSettings(
            trial_days=cfg.trial_days,
            lifetime_price_inr=cfg.lifetime_price_inr,
            currency=cfg.currency,
        ),
        features=FeatureFlags(),
    )


def _row_to_settings(row: dict) -> SystemSettings:
    if not row:
        return _default_settings()
    return SystemSettings(
        subscription=SubscriptionSettings(**row.get("subscription", {})),
        payment=PaymentSettings(**row.get("payment", {})),
        features=FeatureFlags(**row.get("features", {})),
        updated_at=row.get("updated_at"),
    )


def _settings_to_row(settings: SystemSettings) -> dict:
    return {
        "subscription": settings.subscription.model_dump(),
        "payment": settings.payment.model_dump(),
        "features": settings.features.model_dump(),
        "updated_at": settings.updated_at,
    }


class SystemSettingsService:
    def get_settings(self) -> SystemSettings:
        global _cache
        if _cache is not None:
            return _cache
        row = _get_repo().get_system_settings()
        _cache = _row_to_settings(row)
        return _cache

    def get_public_config(self) -> SystemConfigPublic:
        s = self.get_settings()
        return SystemConfigPublic(
            subscription_enabled=s.subscription.subscription_enabled,
            payment_enabled=s.payment.payment_enabled,
            trial_enabled=s.subscription.trial_enabled,
            guest_access_enabled=s.subscription.guest_access_enabled,
            login_required_for_live=s.subscription.login_required_for_live,
            trial_days=s.payment.trial_days,
            lifetime_price_inr=s.payment.lifetime_price_inr,
            currency=s.payment.currency,
            discount_percent=s.payment.discount_percent,
            promotional_message=s.payment.promotional_message,
            features=s.features,
        )

    def update_settings(self, update: SystemSettingsUpdate) -> SystemSettings:
        global _cache
        current = self.get_settings()
        sub = current.subscription.model_copy()
        pay = current.payment.model_copy()
        feat = current.features.model_copy()

        data = update.model_dump(exclude_none=True)
        sub_fields = {
            "subscription_enabled", "trial_enabled",
            "guest_access_enabled", "login_required_for_live",
        }
        pay_fields = {
            "payment_enabled", "trial_days", "lifetime_price_inr",
            "currency", "discount_percent", "promotional_message",
        }
        for key, val in data.items():
            if key in sub_fields:
                setattr(sub, key, val)
            elif key in pay_fields:
                setattr(pay, key, val)
            elif hasattr(feat, key):
                setattr(feat, key, val)

        updated = SystemSettings(
            subscription=sub,
            payment=pay,
            features=feat,
            updated_at=datetime.now(timezone.utc).isoformat(),
        )
        _get_repo().update_system_settings(_settings_to_row(updated))
        _cache = updated
        return updated

    def invalidate_cache(self) -> None:
        global _cache
        _cache = None


_service: Optional[SystemSettingsService] = None


def get_system_settings_service() -> SystemSettingsService:
    global _service
    if _service is None:
        _service = SystemSettingsService()
    return _service
