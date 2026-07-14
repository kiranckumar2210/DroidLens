"""Concrete auth, user, license, and payment service implementations."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from inspectiq.auth.audit_log import (
    log_license_generated,
    log_login,
    log_logout,
    log_premium_activated,
    log_registration,
)
from inspectiq.auth.cloud_auth import (
    cloud_auth_url,
    fetch_cloud_profile,
    license_from_cloud_profile,
    user_from_cloud_profile,
)
from inspectiq.auth.config import get_auth_config
from inspectiq.auth.interfaces import (
    AuthenticationService,
    LicenseService as LicenseServiceInterface,
    PaymentService as PaymentServiceInterface,
    UserService as UserServiceInterface,
)
from inspectiq.auth.license_cache import sign_license_cache
from inspectiq.auth.models import (
    AuthResult,
    AuthSession,
    AuthUser,
    LicenseInfo,
    LicenseStatus,
    LoginRequest,
    OrderStatusResponse,
    OrderSummary,
    PaymentActionResult,
    PurchaseResult,
    RegisterRequest,
    UpdateProfileRequest,
)
from inspectiq.auth.plans import get_plan
from inspectiq.auth.providers.factory import get_payment_provider
from inspectiq.auth.repository import create_auth_repository
from inspectiq.auth.system_settings_service import get_system_settings_service
from inspectiq.auth.security import (
    create_token_pair,
    decode_access_token,
    decode_refresh_token,
)

MERCHANT_NAME = "DroidLens"


class AuthService(AuthenticationService):
    def __init__(self, repo: Optional[Any] = None):
        self._repo = repo or create_auth_repository()
        self._license = LicenseService(self._repo)

    def _build_session(self, user: AuthUser, remember_me: bool = False) -> AuthSession:
        access, access_exp, refresh, refresh_exp, jti = create_token_pair(user.id, remember_me)
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=refresh_exp)
        self._repo.store_refresh_token(user.id, jti, refresh, expires_at)
        license_info = self._repo.get_license(user.id)
        cache = sign_license_cache(user.id, license_info)
        return AuthSession(
            user=user,
            license=license_info,
            access_token=access,
            refresh_token=refresh,
            expires_in=access_exp,
            refresh_expires_in=refresh_exp,
            license_cache=cache,
        )

    def register(self, req: RegisterRequest) -> AuthResult:
        user = self._repo.create_user(req.full_name, req.email, req.password)
        log_registration(user.id, user.email)
        return AuthResult(session=self._build_session(user))

    def login(self, req: LoginRequest) -> AuthResult:
        try:
            user = self._repo.authenticate(req.email, req.password)
        except ValueError as e:
            if str(e) == "Account suspended":
                raise
            raise ValueError("Invalid email or password") from e
        if not user:
            raise ValueError("Invalid email or password")
        log_login(user.id, user.email)
        return AuthResult(session=self._build_session(user, remember_me=req.remember_me))

    def refresh(self, refresh_token: str) -> AuthResult:
        payload = decode_refresh_token(refresh_token)
        if not payload or "sub" not in payload or "jti" not in payload:
            raise ValueError("Invalid refresh token")
        user_id = self._repo.validate_refresh_token(str(payload["jti"]), refresh_token)
        if not user_id or user_id != str(payload["sub"]):
            raise ValueError("Refresh token revoked or expired")
        user = self._repo.get_user(user_id)
        if not user:
            raise ValueError("User not found")
        if user.status == "suspended":
            raise ValueError("Account suspended")
        self._repo.revoke_refresh_token(str(payload["jti"]))
        return AuthResult(session=self._build_session(user))

    def logout(self, user_id: str, refresh_token: Optional[str] = None) -> None:
        log_logout(user_id)
        if refresh_token:
            payload = decode_refresh_token(refresh_token)
            if payload and payload.get("jti"):
                self._repo.revoke_refresh_token(str(payload["jti"]))
        else:
            self._repo.revoke_all_refresh_tokens(user_id)

    def forgot_password(self, email: str) -> dict:
        return {
            "status": "accepted",
            "message": "If an account exists for this email, password reset instructions will be sent.",
        }

    def verify_token(self, token: str) -> Optional[AuthUser]:
        payload = decode_access_token(token)
        if not payload or "sub" not in payload:
            return None
        user = self._repo.get_user(str(payload["sub"]))
        if user:
            return user
        if cloud_auth_url():
            profile = fetch_cloud_profile(token)
            return user_from_cloud_profile(profile) if profile else None
        return None

    def change_password(self, user_id: str, current: str, new_password: str) -> None:
        self._repo.change_password(user_id, current, new_password)
        self._repo.revoke_all_refresh_tokens(user_id)

    def delete_account(self, user_id: str, password: str) -> None:
        self._repo.delete_user(user_id, password)


class UserService(UserServiceInterface):
    def __init__(self, repo: Optional[Any] = None):
        self._repo = repo or create_auth_repository()

    def get_profile(self, user_id: str) -> AuthUser:
        user = self._repo.get_user(user_id)
        if not user:
            raise ValueError("User not found")
        return user

    def update_profile(self, user_id: str, req: UpdateProfileRequest) -> AuthUser:
        return self._repo.update_user(user_id, req.full_name, req.avatar_url)

    def get_purchase_history(self, user_id: str) -> list[OrderSummary]:
        cfg = get_auth_config()
        orders = []
        for row in self._repo.list_user_orders(user_id):
            orders.append(OrderSummary(
                id=row["id"],
                order_id=row["order_id"],
                transaction_id=row.get("transaction_id"),
                merchant_transaction_id=row.get("merchant_transaction_id"),
                phonepe_transaction_id=row.get("phonepe_transaction_id"),
                amount_inr=row["amount_inr"],
                currency=row.get("currency", cfg.currency),
                status=row["status"],
                payment_provider=row.get("payment_provider", cfg.payment_provider),
                payment_method=row.get("payment_method"),
                plan_id=row["plan_id"],
                created_at=row["created_at"],
                completed_at=row.get("completed_at"),
            ))
        return orders


class LicenseService(LicenseServiceInterface):
    def __init__(self, repo: Optional[Any] = None):
        self._repo = repo or create_auth_repository()

    def get_license(self, user_id: str, access_token: Optional[str] = None) -> LicenseInfo:
        try:
            return self._repo.get_license(user_id)
        except ValueError:
            if access_token and cloud_auth_url():
                profile = fetch_cloud_profile(access_token)
                if profile:
                    lic = license_from_cloud_profile(profile)
                    if lic:
                        return lic
            raise

    def has_premium_access(self, user_id: Optional[str], access_token: Optional[str] = None) -> bool:
        if not user_id:
            return False
        settings = get_system_settings_service().get_settings()
        if not settings.subscription.subscription_enabled:
            user = self._repo.get_user(user_id)
            if user:
                return bool(user and user.status != "suspended")
            if access_token and cloud_auth_url():
                profile = fetch_cloud_profile(access_token)
                cloud_user = user_from_cloud_profile(profile) if profile else None
                return bool(cloud_user and cloud_user.status != "suspended")
            return False
        try:
            return self.get_license(user_id, access_token=access_token).has_premium
        except ValueError:
            return False

    def activate_plan(self, user_id: str, plan_id: str, payment_ref: Optional[str] = None) -> LicenseInfo:
        plan = get_plan(plan_id)
        if not plan:
            raise ValueError(f"Unknown plan: {plan_id}")
        if plan_id == "lifetime":
            info = self._repo.activate_lifetime(user_id, payment_ref)
            log_license_generated(user_id, info.license_id or f"lifetime-{user_id}", "lifetime")
            log_premium_activated(user_id, "lifetime")
            return info
        raise ValueError(f"Plan activation not implemented: {plan_id}")

    def start_trial(self, user_id: str) -> LicenseInfo:
        return self._repo.get_license(user_id)


class PaymentService(PaymentServiceInterface):
    """Delegates to pluggable PaymentProvider — swap gateway without UI changes."""

    def __init__(self, repo: Optional[Any] = None):
        self._repo = repo or create_auth_repository()
        self._license = LicenseService(self._repo)
        self._provider = get_payment_provider(self._repo)

    def _build_checkout(self, payment: dict, user: AuthUser) -> PurchaseResult:
        plan = get_plan(payment["plan_id"])
        if not plan:
            raise ValueError("Unknown plan")
        cfg = get_auth_config()
        provider_name = payment.get("payment_provider", self._provider.name)
        merchant = "DroidLens" if provider_name != "phonepe" else "PhonePe"
        return PurchaseResult(
            payment_id=payment["id"],
            order_id=payment["order_id"],
            transaction_id=payment.get("phonepe_transaction_id") or payment["transaction_id"],
            plan_id=payment["plan_id"],
            plan_name=plan.name,
            amount_inr=payment["amount_inr"],
            currency=payment.get("currency", cfg.currency),
            status=payment["status"],
            payment_provider=provider_name,
            merchant_name=merchant,
            customer_email=user.email,
            checkout_url=payment.get("checkout_url"),
        )

    def create_purchase(self, user_id: str, plan_id: str) -> PurchaseResult:
        settings = get_system_settings_service().get_settings()
        if not settings.subscription.subscription_enabled:
            raise ValueError("Subscription system is disabled")
        if not settings.payment.payment_enabled:
            raise ValueError("Payments are disabled")
        user = self._repo.get_user(user_id)
        if not user:
            raise ValueError("User not found")
        license_info = self._license.get_license(user_id)
        if license_info.status == LicenseStatus.LIFETIME:
            raise ValueError("Lifetime license already active")
        plan = get_plan(plan_id)
        if not plan or plan.price_inr is None:
            raise ValueError("Invalid or free plan")
        cfg = get_auth_config()
        record = self._provider.create_order(user_id, plan_id, plan.price_inr, cfg.currency)
        checkout = self._build_checkout(record.to_dict(), user)
        return checkout

    def sync_order_status(self, user_id: str, payment_id: str) -> OrderStatusResponse:
        """Poll gateway + return status — PhonePe license activation is webhook-only."""
        from inspectiq.auth.providers.phonepe import PhonePePaymentProvider

        if isinstance(self._provider, PhonePePaymentProvider):
            self._provider.sync_order_status(user_id, payment_id)
        else:
            payment = self._repo.get_payment(payment_id, user_id)
            if not payment:
                raise ValueError("Payment not found")

        payment = self._repo.get_payment(payment_id, user_id)
        if not payment:
            raise ValueError("Payment not found")

        license_info = self._license.get_license(user_id)
        return OrderStatusResponse(
            payment_id=payment["id"],
            order_id=payment["order_id"],
            status=payment["status"],
            payment_provider=payment.get("payment_provider", self._provider.name),
            payment_method=payment.get("payment_method"),
            phonepe_transaction_id=payment.get("phonepe_transaction_id"),
            license=license_info,
            checkout_url=payment.get("checkout_url"),
        )

    def get_checkout(self, user_id: str, payment_id: str) -> PurchaseResult:
        user = self._repo.get_user(user_id)
        if not user:
            raise ValueError("User not found")
        payment = self._repo.get_payment(payment_id, user_id)
        if not payment:
            raise ValueError("Payment not found")
        return self._build_checkout(payment, user)

    def confirm_purchase(self, user_id: str, payment_id: str) -> LicenseInfo:
        settings = get_system_settings_service().get_settings()
        if not settings.subscription.subscription_enabled or not settings.payment.payment_enabled:
            raise ValueError("Payments are disabled")
        cfg = get_auth_config()
        if cfg.payment_provider == "phonepe":
            raise ValueError(
                "PhonePe payments are confirmed via webhook only. "
                "Use GET /payment/status/{payment_id} to check order status."
            )
        self._provider.verify_payment(user_id, payment_id)
        plan_id = self._repo.get_payment_plan_id(payment_id)
        return self._license.activate_plan(user_id, plan_id, payment_ref=payment_id)

    def fail_purchase(self, user_id: str, payment_id: str) -> LicenseInfo:
        self._provider.fail(user_id, payment_id)
        return self._license.get_license(user_id)

    def cancel_purchase(self, user_id: str, payment_id: str) -> LicenseInfo:
        self._provider.cancel(user_id, payment_id)
        return self._license.get_license(user_id)

    def refund_purchase(self, user_id: str, payment_id: str) -> LicenseInfo:
        self._provider.refund(user_id, payment_id)
        return self._license.get_license(user_id)

    def handle_webhook(self, payload: dict, authorization: Optional[str] = None) -> Optional[dict]:
        record = self._provider.webhook(payload, authorization=authorization)
        if not record:
            return None
        return record.to_dict()

    def payment_action_result(self, user_id: str, payment_id: str, license_info: LicenseInfo) -> PaymentActionResult:
        payment = self._repo.get_payment(payment_id, user_id)
        status = payment["status"] if payment else "unknown"
        return PaymentActionResult(payment_id=payment_id, status=status, license=license_info)


def guest_license() -> LicenseInfo:
    return LicenseInfo(
        status=LicenseStatus.GUEST,
        plan_id="guest",
        plan_name="Guest",
        has_premium=False,
    )
