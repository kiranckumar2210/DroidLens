"""Structured audit logging for auth, payment, and licensing events."""

from __future__ import annotations

from typing import Optional

from inspectiq.logging_config import get_logger

logger = get_logger("droidlens.auth.audit")

_repo = None


def _get_repo():
    global _repo
    if _repo is None:
        from inspectiq.auth.repository import create_auth_repository
        _repo = create_auth_repository()
    return _repo


def configure_audit_repo(repo) -> None:
    """Replace audit persistence target — used by unit tests."""
    global _repo
    _repo = repo


def _persist(
    action: str,
    *,
    user_id: Optional[str] = None,
    user_email: Optional[str] = None,
    status: str = "success",
    detail: Optional[str] = None,
) -> None:
    try:
        _get_repo().record_audit_event(
            action,
            user_id=user_id,
            user_email=user_email,
            status=status,
            detail=detail,
        )
    except Exception as exc:
        logger.warning("audit_persist_failed action=%s error=%s", action, exc)


def log_registration(user_id: str, email: str) -> None:
    logger.info("registration user_id=%s email=%s", user_id, email)
    _persist("registration", user_id=user_id, user_email=email)


def log_login(user_id: str, email: str) -> None:
    logger.info("login user_id=%s email=%s", user_id, email)
    _persist("login", user_id=user_id, user_email=email)


def log_logout(user_id: str) -> None:
    logger.info("logout user_id=%s", user_id)
    _persist("logout", user_id=user_id)


def log_order_created(user_id: str, order_id: str, amount: int, provider: str) -> None:
    logger.info("order_created user_id=%s order_id=%s amount=%s provider=%s", user_id, order_id, amount, provider)
    _persist("order_created", user_id=user_id, detail=f"order={order_id} amount={amount} provider={provider}")


def log_payment_started(user_id: str, order_id: str) -> None:
    logger.info("payment_started user_id=%s order_id=%s", user_id, order_id)
    _persist("payment_started", user_id=user_id, detail=f"order={order_id}")


def log_payment_success(user_id: str, order_id: str, transaction_id: str) -> None:
    logger.info("payment_success user_id=%s order_id=%s transaction_id=%s", user_id, order_id, transaction_id)
    _persist("payment_success", user_id=user_id, detail=f"order={order_id} txn={transaction_id}")


def log_payment_failure(user_id: str, order_id: str, reason: str = "") -> None:
    logger.warning("payment_failure user_id=%s order_id=%s reason=%s", user_id, order_id, reason)
    _persist("payment_failure", user_id=user_id, status="failure", detail=f"order={order_id} reason={reason}")


def log_license_generated(user_id: str, license_id: str, license_type: str) -> None:
    logger.info("license_generated user_id=%s license_id=%s type=%s", user_id, license_id, license_type)
    _persist("license_generated", user_id=user_id, detail=f"license={license_id} type={license_type}")


def log_premium_activated(user_id: str, license_type: str) -> None:
    logger.info("premium_activated user_id=%s license_type=%s", user_id, license_type)
    _persist("premium_activated", user_id=user_id, detail=f"type={license_type}")


def log_payment_redirect_generated(user_id: str, order_id: str, provider: str) -> None:
    logger.info("redirect_url_generated user_id=%s order_id=%s provider=%s", user_id, order_id, provider)
    _persist("payment_redirect", user_id=user_id, detail=f"order={order_id} provider={provider}")


def log_payment_callback_received(order_id: str, provider: str) -> None:
    logger.info("payment_callback_received order_id=%s provider=%s", order_id, provider)
    _persist("payment_callback", detail=f"order={order_id} provider={provider}")


def log_webhook_received(event: str, order_id: str, provider: str = "phonepe") -> None:
    logger.info("webhook_received event=%s order_id=%s provider=%s", event, order_id, provider)
    _persist("webhook_received", detail=f"event={event} order={order_id} provider={provider}")


def log_webhook_verification_failed(provider: str = "phonepe") -> None:
    logger.warning("webhook_verification_failed provider=%s", provider)
    _persist("webhook_verification_failed", status="failure", detail=f"provider={provider}")


def log_webhook_verification_passed(event: str, order_id: str, provider: str = "phonepe") -> None:
    logger.info("webhook_verification_passed event=%s order_id=%s provider=%s", event, order_id, provider)
    _persist("webhook_verification_passed", detail=f"event={event} order={order_id} provider={provider}")


def log_refund_processed(user_id: str, order_id: str) -> None:
    logger.info("refund_processed user_id=%s order_id=%s", user_id, order_id)
    _persist("refund_processed", user_id=user_id, detail=f"order={order_id}")


def log_admin_action(
    admin_id: str,
    action: str,
    *,
    target_user_id: Optional[str] = None,
    detail: Optional[str] = None,
) -> None:
    logger.info("admin_action admin_id=%s action=%s target=%s", admin_id, action, target_user_id)
    full_detail = detail or ""
    if target_user_id:
        full_detail = f"target={target_user_id} {full_detail}".strip()
    _persist(f"admin_{action}", user_id=admin_id, detail=full_detail or None)


def log_settings_change(
    admin_id: str,
    admin_email: str,
    field: str,
    old_value: str,
    new_value: str,
    ip: str = "unknown",
) -> None:
    detail = f"field={field} old={old_value} new={new_value} ip={ip}"
    logger.info("settings_change admin_id=%s %s", admin_id, detail)
    _persist("settings_change", user_id=admin_id, user_email=admin_email, detail=detail)
