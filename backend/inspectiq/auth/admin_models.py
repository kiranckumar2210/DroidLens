"""Admin dashboard API models."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from inspectiq.auth.models import AuthUser, LicenseInfo


class AdminKpiCards(BaseModel):
    total_registered_users: int = 0
    active_trial_users: int = 0
    lifetime_subscribers: int = 0
    guest_sessions_today: int = 0
    total_revenue_inr: int = 0
    trial_conversion_rate: float = 0.0
    payments_today: int = 0
    active_sessions: int = 0


class RegistrationStats(BaseModel):
    today: int = 0
    yesterday: int = 0
    this_week: int = 0
    this_month: int = 0
    total: int = 0
    period: str = "30d"
    daily: List[dict] = Field(default_factory=list)


class RevenueStats(BaseModel):
    today_inr: int = 0
    week_inr: int = 0
    month_inr: int = 0
    total_inr: int = 0
    arpu_inr: float = 0.0
    period: str = "30d"


class PaymentStats(BaseModel):
    total_orders: int = 0
    successful: int = 0
    failed: int = 0
    pending: int = 0
    refunded: int = 0
    success_rate: float = 0.0


class SubscriptionStats(BaseModel):
    trial_active: int = 0
    trial_expired: int = 0
    lifetime_users: int = 0
    conversion_rate: float = 0.0


class AdminUserRow(BaseModel):
    id: str
    full_name: str
    email: str
    role: str = "user"
    registration_date: datetime
    license_type: str
    license_status: str
    trial_status: str
    payment_status: str
    last_login: Optional[datetime] = None
    account_status: str = "active"


class AdminPaymentRow(BaseModel):
    id: str
    order_id: str
    transaction_id: Optional[str] = None
    user_id: str
    user_name: str
    user_email: str
    amount_inr: int
    currency: str = "INR"
    payment_provider: str
    payment_method: Optional[str] = None
    status: str
    plan_id: str
    created_at: datetime
    completed_at: Optional[datetime] = None


class ActivityEvent(BaseModel):
    id: str
    timestamp: datetime
    user_id: Optional[str] = None
    user_email: Optional[str] = None
    action: str
    status: str = "success"
    detail: Optional[str] = None


class PaginatedUsers(BaseModel):
    items: List[AdminUserRow]
    total: int
    page: int
    page_size: int


class PaginatedPayments(BaseModel):
    items: List[AdminPaymentRow]
    total: int
    page: int
    page_size: int


class AdminDashboardResponse(BaseModel):
    kpis: AdminKpiCards
    registration: RegistrationStats
    revenue: RevenueStats
    payments: PaymentStats
    subscriptions: SubscriptionStats
    recent_users: List[AdminUserRow] = Field(default_factory=list)
    recent_payments: List[AdminPaymentRow] = Field(default_factory=list)
    recent_activity: List[ActivityEvent] = Field(default_factory=list)
    updated_at: datetime


class AdminUserDetail(BaseModel):
    user: AuthUser
    license: LicenseInfo
    orders: List[dict] = Field(default_factory=list)


class AdminUserUpdate(BaseModel):
    full_name: Optional[str] = None
    status: Optional[str] = None
    role: Optional[str] = None


class AdminActionResult(BaseModel):
    ok: bool = True
    message: str = ""
