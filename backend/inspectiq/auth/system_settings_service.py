"""Singleton system settings service with in-memory cache."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel

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


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.lower() in ("1", "true", "yes")


def _default_settings() -> SystemSettings:
    cfg = get_auth_config()
    subscription_on = _env_bool("DROIDLENS_SUBSCRIPTION_ENABLED", default=False)
    return SystemSettings(
        subscription=SubscriptionSettings(subscription_enabled=subscription_on),
        payment=PaymentSettings(
            payment_enabled=subscription_on,
            trial_days=cfg.trial_days,
            lifetime_price_inr=cfg.lifetime_price_inr,
            currency=cfg.currency,
        ),
        features=FeatureFlags(),
    )


def _merge_model(default: BaseModel, overrides: dict) -> BaseModel:
    data = {**default.model_dump(), **(overrides or {})}
    return type(default)(**data)


def _apply_env_overrides(settings: SystemSettings) -> SystemSettings:
    """When DROIDLENS_SUBSCRIPTION_ENABLED is set, it overrides stored DB settings."""
    if "DROIDLENS_SUBSCRIPTION_ENABLED" not in os.environ:
        return settings
    enabled = _env_bool("DROIDLENS_SUBSCRIPTION_ENABLED", default=False)
    sub = settings.subscription.model_copy(update={"subscription_enabled": enabled})
    pay = settings.payment.model_copy()
    if not enabled:
        pay = pay.model_copy(update={"payment_enabled": False})
    return settings.model_copy(update={"subscription": sub, "payment": pay})


def _row_to_settings(row: dict) -> SystemSettings:
    defaults = _default_settings()
    if not row:
        return defaults
    return SystemSettings(
        subscription=_merge_model(defaults.subscription, row.get("subscription", {})),
        payment=_merge_model(defaults.payment, row.get("payment", {})),
        features=_merge_model(defaults.features, row.get("features", {})),
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
            return _apply_env_overrides(_cache)
        row = _get_repo().get_system_settings()
        if not row:
            defaults = _default_settings()
            _get_repo().update_system_settings(_settings_to_row(defaults))
            _cache = defaults
            return _apply_env_overrides(_cache)
        _cache = _row_to_settings(row)
        return _apply_env_overrides(_cache)

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

        if data.get("subscription_enabled") is False and "payment_enabled" not in data:
            pay.payment_enabled = False

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
