"""System-wide licensing and feature configuration models."""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class LicenseOverrideType(str, Enum):
    GUEST = "guest"
    TRIAL = "trial"
    PREMIUM = "premium"
    LIFETIME = "lifetime"
    EXPIRED = "expired"
    SUSPENDED = "suspended"


class FeatureFlags(BaseModel):
    mock_inspector: bool = True
    live_inspector: bool = True
    recorder: bool = True
    xml_upload: bool = True
    screenshot_upload: bool = True
    locator_builder: bool = True
    code_generator: bool = True
    ai_features: bool = True
    export: bool = True
    device_manager: bool = True
    session_manager: bool = True


class SubscriptionSettings(BaseModel):
    subscription_enabled: bool = False
    trial_enabled: bool = True
    guest_access_enabled: bool = True
    login_required_for_live: bool = True


class PaymentSettings(BaseModel):
    payment_enabled: bool = False
    trial_days: int = 7
    lifetime_price_inr: int = 199
    currency: str = "INR"
    discount_percent: int = 0
    promotional_message: str = ""


class SystemSettings(BaseModel):
    subscription: SubscriptionSettings = Field(default_factory=SubscriptionSettings)
    payment: PaymentSettings = Field(default_factory=PaymentSettings)
    features: FeatureFlags = Field(default_factory=FeatureFlags)
    updated_at: Optional[str] = None


class SystemSettingsUpdate(BaseModel):
    subscription_enabled: Optional[bool] = None
    payment_enabled: Optional[bool] = None
    trial_enabled: Optional[bool] = None
    guest_access_enabled: Optional[bool] = None
    login_required_for_live: Optional[bool] = None
    trial_days: Optional[int] = None
    lifetime_price_inr: Optional[int] = None
    currency: Optional[str] = None
    discount_percent: Optional[int] = None
    promotional_message: Optional[str] = None
    mock_inspector: Optional[bool] = None
    live_inspector: Optional[bool] = None
    recorder: Optional[bool] = None
    xml_upload: Optional[bool] = None
    screenshot_upload: Optional[bool] = None
    locator_builder: Optional[bool] = None
    code_generator: Optional[bool] = None
    ai_features: Optional[bool] = None
    export: Optional[bool] = None
    device_manager: Optional[bool] = None
    session_manager: Optional[bool] = None


class SystemConfigPublic(BaseModel):
    """Public-facing config for frontend — no auth required."""

    subscription_enabled: bool = False
    payment_enabled: bool = False
    trial_enabled: bool = True
    guest_access_enabled: bool = True
    login_required_for_live: bool = True
    trial_days: int = 7
    lifetime_price_inr: int = 199
    currency: str = "INR"
    discount_percent: int = 0
    promotional_message: str = ""
    features: FeatureFlags = Field(default_factory=FeatureFlags)


class SetLicenseRequest(BaseModel):
    license_type: LicenseOverrideType
