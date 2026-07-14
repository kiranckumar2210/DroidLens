"""Admin dashboard business logic."""

from __future__ import annotations

import csv
import io
from datetime import datetime, timezone
from typing import Any, Optional

from inspectiq.auth.admin_models import (
    ActivityEvent,
    AdminActionResult,
    AdminDashboardResponse,
    AdminKpiCards,
    AdminPaymentRow,
    AdminUserDetail,
    AdminUserRow,
    AdminUserUpdate,
    PaginatedPayments,
    PaginatedUsers,
    PaymentStats,
    RegistrationStats,
    RevenueStats,
    SubscriptionStats,
)
from inspectiq.auth.audit_log import log_admin_action, log_settings_change
from inspectiq.auth.repository import create_auth_repository
from inspectiq.auth.system_settings_models import SetLicenseRequest, SystemSettings, SystemSettingsUpdate
from inspectiq.auth.system_settings_service import get_system_settings_service


class AdminService:
    def __init__(self, repo: Optional[Any] = None):
        self._repo = repo or create_auth_repository()

    def get_dashboard(self) -> AdminDashboardResponse:
        kpis = AdminKpiCards(**self._repo.admin_get_kpis())
        registration = RegistrationStats(**self._repo.admin_registration_stats())
        revenue = RevenueStats(**self._repo.admin_revenue_stats())
        payments = PaymentStats(**self._repo.admin_payment_stats())
        subscriptions = SubscriptionStats(**self._repo.admin_subscription_stats())
        recent_users = [AdminUserRow(**r) for r in self._repo.admin_get_recent_users()]
        recent_payments = [AdminPaymentRow(**r) for r in self._repo.admin_get_recent_payments()]
        events, _ = self._repo.list_audit_events(limit=15)
        recent_activity = [ActivityEvent(**e) for e in events]
        return AdminDashboardResponse(
            kpis=kpis,
            registration=registration,
            revenue=revenue,
            payments=payments,
            subscriptions=subscriptions,
            recent_users=recent_users,
            recent_payments=recent_payments,
            recent_activity=recent_activity,
            updated_at=datetime.now(timezone.utc),
        )

    def list_users(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        status_filter: Optional[str] = None,
        license_filter: Optional[str] = None,
        sort_by: str = "created_at",
        sort_dir: str = "desc",
    ) -> PaginatedUsers:
        items, total = self._repo.admin_list_users(
            page=page,
            page_size=page_size,
            search=search,
            status_filter=status_filter,
            license_filter=license_filter,
            sort_by=sort_by,
            sort_dir=sort_dir,
        )
        return PaginatedUsers(
            items=[AdminUserRow(**r) for r in items],
            total=total,
            page=page,
            page_size=page_size,
        )

    def count_users(self) -> int:
        return self._repo.admin_count_users()

    def get_recent_users(self, limit: int = 10) -> list[AdminUserRow]:
        return [AdminUserRow(**r) for r in self._repo.admin_get_recent_users(limit)]

    def get_user(self, user_id: str) -> AdminUserDetail:
        detail = self._repo.admin_get_user_detail(user_id)
        if not detail:
            raise ValueError("User not found")
        return AdminUserDetail(
            user=detail["user"],
            license=detail["license"],
            orders=detail["orders"],
        )

    def update_user(self, admin_id: str, user_id: str, req: AdminUserUpdate) -> AdminUserDetail:
        self._repo.admin_update_user(
            user_id,
            full_name=req.full_name,
            status=req.status,
            role=req.role,
        )
        log_admin_action(admin_id, "user_update", target_user_id=user_id, detail=str(req.model_dump(exclude_none=True)))
        return self.get_user(user_id)

    def delete_user(self, admin_id: str, user_id: str) -> AdminActionResult:
        self._repo.admin_delete_user(user_id)
        log_admin_action(admin_id, "user_delete", target_user_id=user_id)
        return AdminActionResult(ok=True, message="User deleted")

    def reset_trial(self, admin_id: str, user_id: str) -> AdminActionResult:
        self._repo.admin_reset_trial(user_id)
        log_admin_action(admin_id, "reset_trial", target_user_id=user_id)
        return AdminActionResult(ok=True, message="Trial reset")

    def activate_license(self, admin_id: str, user_id: str) -> AdminActionResult:
        self._repo.activate_lifetime(user_id, payment_ref="admin-grant")
        log_admin_action(admin_id, "activate_license", target_user_id=user_id)
        return AdminActionResult(ok=True, message="Lifetime license activated")

    def set_license(self, admin_id: str, user_id: str, req: SetLicenseRequest) -> AdminActionResult:
        self._repo.admin_set_license(user_id, req.license_type.value)
        log_admin_action(
            admin_id,
            "set_license",
            target_user_id=user_id,
            detail=f"type={req.license_type.value}",
        )
        return AdminActionResult(ok=True, message=f"License set to {req.license_type.value}")

    def get_licensing_settings(self) -> SystemSettings:
        return get_system_settings_service().get_settings()

    def update_licensing_settings(
        self,
        admin_id: str,
        admin_email: str,
        update: SystemSettingsUpdate,
        ip: str = "unknown",
    ) -> SystemSettings:
        svc = get_system_settings_service()
        before = svc.get_settings()
        after = svc.update_settings(update)

        changes = update.model_dump(exclude_none=True)
        for field, new_val in changes.items():
            old_val = None
            if field in {"subscription_enabled", "trial_enabled", "guest_access_enabled", "login_required_for_live"}:
                old_val = getattr(before.subscription, field, None)
            elif field in {"payment_enabled", "trial_days", "lifetime_price_inr", "currency", "discount_percent", "promotional_message"}:
                old_val = getattr(before.payment, field, None)
            elif hasattr(before.features, field):
                old_val = getattr(before.features, field, None)
            if old_val != new_val:
                log_settings_change(admin_id, admin_email, field, str(old_val), str(new_val), ip)

        log_admin_action(admin_id, "update_settings", detail=str(changes))
        return after

    def suspend_user(self, admin_id: str, user_id: str) -> AdminActionResult:
        self._repo.admin_suspend_user(user_id)
        log_admin_action(admin_id, "suspend_user", target_user_id=user_id)
        return AdminActionResult(ok=True, message="User suspended")

    def list_payments(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        status_filter: Optional[str] = None,
        sort_by: str = "created_at",
        sort_dir: str = "desc",
    ) -> PaginatedPayments:
        items, total = self._repo.admin_list_payments(
            page=page,
            page_size=page_size,
            search=search,
            status_filter=status_filter,
            sort_by=sort_by,
            sort_dir=sort_dir,
        )
        return PaginatedPayments(
            items=[AdminPaymentRow(**r) for r in items],
            total=total,
            page=page,
            page_size=page_size,
        )

    def get_revenue(self, period: str = "30d") -> RevenueStats:
        return RevenueStats(**self._repo.admin_revenue_stats(period))

    def get_subscriptions(self) -> SubscriptionStats:
        return SubscriptionStats(**self._repo.admin_subscription_stats())

    def list_activity(
        self,
        *,
        page: int = 1,
        page_size: int = 50,
        action: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> dict:
        offset = (max(1, page) - 1) * page_size
        events, total = self._repo.list_audit_events(
            limit=page_size,
            offset=offset,
            action=action,
            user_id=user_id,
        )
        return {
            "items": [ActivityEvent(**e) for e in events],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    def get_statistics(self) -> dict:
        return {
            "registration": self._repo.admin_registration_stats(),
            "revenue": self._repo.admin_revenue_stats(),
            "payments": self._repo.admin_payment_stats(),
            "subscriptions": self._repo.admin_subscription_stats(),
            "kpis": self._repo.admin_get_kpis(),
        }

    def export_users_csv(
        self,
        *,
        search: Optional[str] = None,
        status_filter: Optional[str] = None,
        license_filter: Optional[str] = None,
    ) -> str:
        items, _ = self._repo.admin_list_users(
            page=1,
            page_size=10000,
            search=search,
            status_filter=status_filter,
            license_filter=license_filter,
        )
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow([
            "id", "full_name", "email", "role", "registration_date",
            "license_type", "license_status", "trial_status", "payment_status",
            "last_login", "account_status",
        ])
        for row in items:
            writer.writerow([
                row["id"],
                row["full_name"],
                row["email"],
                row["role"],
                row["registration_date"].isoformat() if row["registration_date"] else "",
                row["license_type"],
                row["license_status"],
                row["trial_status"],
                row["payment_status"],
                row["last_login"].isoformat() if row["last_login"] else "",
                row["account_status"],
            ])
        return buf.getvalue()

    def export_payments_csv(
        self,
        *,
        search: Optional[str] = None,
        status_filter: Optional[str] = None,
    ) -> str:
        items, _ = self._repo.admin_list_payments(
            page=1,
            page_size=10000,
            search=search,
            status_filter=status_filter,
        )
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow([
            "id", "order_id", "transaction_id", "user_id", "user_name", "user_email",
            "amount_inr", "currency", "payment_provider", "payment_method",
            "status", "plan_id", "created_at", "completed_at",
        ])
        for row in items:
            writer.writerow([
                row["id"],
                row["order_id"],
                row["transaction_id"] or "",
                row["user_id"],
                row["user_name"],
                row["user_email"],
                row["amount_inr"],
                row["currency"],
                row["payment_provider"],
                row["payment_method"] or "",
                row["status"],
                row["plan_id"],
                row["created_at"].isoformat() if row["created_at"] else "",
                row["completed_at"].isoformat() if row["completed_at"] else "",
            ])
        return buf.getvalue()
