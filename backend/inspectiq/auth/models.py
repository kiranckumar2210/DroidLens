"""Auth & licensing domain models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


class LicenseStatus(str, Enum):
    GUEST = "guest"
    TRIAL_ACTIVE = "trial_active"
    TRIAL_EXPIRED = "trial_expired"
    PAYMENT_PENDING = "payment_pending"
    LIFETIME = "lifetime"
    SUBSCRIPTION_ACTIVE = "subscription_active"
    SUBSCRIPTION_EXPIRED = "subscription_expired"


class PaymentStatus(str, Enum):
    CREATED = "created"
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class AuthUser(BaseModel):
    id: str
    full_name: str
    email: EmailStr
    created_at: datetime
    avatar_url: Optional[str] = None
    last_login: Optional[datetime] = None
    status: str = "active"
    role: str = "user"


class LicenseInfo(BaseModel):
    status: LicenseStatus
    plan_id: str
    plan_name: str
    trial_started_at: Optional[datetime] = None
    trial_expires_at: Optional[datetime] = None
    license_activated_at: Optional[datetime] = None
    license_expires_at: Optional[datetime] = None
    days_remaining: Optional[int] = None
    has_premium: bool = False
    price_inr: Optional[int] = None
    pending_payment_id: Optional[str] = None
    license_id: Optional[str] = None


class AuthSession(BaseModel):
    user: AuthUser
    license: LicenseInfo
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 3600
    refresh_expires_in: int = 2592000
    license_cache: Optional[str] = None


class AuthResult(BaseModel):
    session: AuthSession


class RegisterRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    confirm_password: str

    @field_validator("full_name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        return v.strip()

    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, v: str, info) -> str:
        if "password" in info.data and v != info.data["password"]:
            raise ValueError("Passwords do not match")
        return v

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    remember_me: bool = False


class RefreshRequest(BaseModel):
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class LogoutRequest(BaseModel):
    refresh_token: Optional[str] = None


class UpdateProfileRequest(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=120)
    avatar_url: Optional[str] = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)
    confirm_password: str

    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, v: str, info) -> str:
        if "new_password" in info.data and v != info.data["new_password"]:
            raise ValueError("Passwords do not match")
        return v


class PurchaseRequest(BaseModel):
    plan_id: str = "lifetime"


class PurchaseResult(BaseModel):
    payment_id: str
    order_id: str
    transaction_id: str
    plan_id: str
    plan_name: str
    amount_inr: int
    currency: str = "INR"
    status: str
    payment_provider: str = "mock"
    merchant_name: str = "DroidLens"
    customer_email: Optional[EmailStr] = None
    checkout_url: Optional[str] = None


class PaymentActionResult(BaseModel):
    payment_id: str
    status: str
    license: LicenseInfo


class OrderSummary(BaseModel):
    id: str
    order_id: str
    transaction_id: Optional[str] = None
    merchant_transaction_id: Optional[str] = None
    phonepe_transaction_id: Optional[str] = None
    amount_inr: int
    currency: str = "INR"
    status: str
    payment_provider: str = "mock"
    payment_method: Optional[str] = None
    plan_id: str
    created_at: datetime
    completed_at: Optional[datetime] = None


class OrderStatusResponse(BaseModel):
    payment_id: str
    order_id: str
    status: str
    payment_provider: str
    payment_method: Optional[str] = None
    phonepe_transaction_id: Optional[str] = None
    license: LicenseInfo
    checkout_url: Optional[str] = None


class PlanPublic(BaseModel):
    id: str
    name: str
    description: str
    price_inr: Optional[int]
    billing_period: str
    trial_days: int = 0
    features: List[str] = Field(default_factory=list)


class PricingResponse(BaseModel):
    lifetime_price_inr: int
    currency: str
    payment_provider: str
    trial_days: int
    plans: List[PlanPublic]


class AccountSummary(BaseModel):
    user: AuthUser
    license: LicenseInfo
    app_version: str = "1.0.0"
    purchase_history: List[OrderSummary] = Field(default_factory=list)
    license_cache: Optional[str] = None
