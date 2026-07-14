"""PhonePe Payment Gateway provider — implements PaymentProvider contract."""

from __future__ import annotations

from typing import Any, Optional
from urllib.parse import urlencode, urlparse, urlunparse

from inspectiq.auth.audit_log import (
    log_order_created,
    log_payment_failure,
    log_payment_redirect_generated,
    log_payment_started,
    log_payment_success,
    log_refund_processed,
    log_webhook_received,
    log_webhook_verification_failed,
    log_webhook_verification_passed,
)
from inspectiq.auth.config import get_auth_config
from inspectiq.auth.providers.base import OrderRecord, PaymentProvider
from inspectiq.logging_config import get_logger
from inspectiq.payment.phonepe.client import PhonePeService
from inspectiq.payment.phonepe.config import get_phonepe_config
from inspectiq.payment.phonepe.dto import PhonePePayRequest
from inspectiq.payment.phonepe.webhook import parse_webhook_event, webhook_event_id

logger = get_logger("droidlens.payment.phonepe.provider")

INITIATED_STATUSES = ("pending", "created", "initiated", "processing")
TERMINAL_STATUSES = ("completed", "failed", "cancelled", "refunded")


class PhonePePaymentProvider(PaymentProvider):
    def __init__(self, repo: Any):
        self._repo = repo
        self._phonepe = PhonePeService()

    @property
    def name(self) -> str:
        return "phonepe"

    def _to_record(self, row: dict) -> OrderRecord:
        return OrderRecord(
            id=row["id"],
            user_id=row["user_id"],
            order_id=row["order_id"],
            transaction_id=row.get("transaction_id") or "",
            plan_id=row["plan_id"],
            amount=row.get("amount_inr") or row.get("amount", 0),
            currency=row.get("currency", get_auth_config().currency),
            status=row["status"],
            payment_provider=row.get("payment_provider", self.name),
            created_at=row.get("created_at"),
            completed_at=row.get("completed_at"),
            checkout_url=row.get("checkout_url"),
            payment_method=row.get("payment_method"),
            phonepe_order_id=row.get("phonepe_order_id"),
            phonepe_transaction_id=row.get("phonepe_transaction_id"),
            merchant_transaction_id=row.get("merchant_transaction_id") or row["order_id"],
        )

    def _redirect_url(self, payment_id: str) -> str:
        cfg = get_phonepe_config()
        base = cfg.callback_url
        parsed = urlparse(base)
        query = urlencode({"payment_id": payment_id, "payment_return": "1"})
        if parsed.query:
            query = f"{parsed.query}&{query}"
        return urlunparse(parsed._replace(query=query))

    def create_order(self, user_id: str, plan_id: str, amount: int, currency: str) -> OrderRecord:
        existing = self._repo.get_pending_payment(user_id)
        if existing and existing.get("checkout_url"):
            log_payment_started(user_id, existing["order_id"])
            return self._to_record(existing)

        row = self._repo.create_payment(user_id, plan_id, amount, currency=currency, payment_provider=self.name)
        log_order_created(user_id, row["order_id"], amount, self.name)

        amount_paisa = amount * 100
        redirect = self._redirect_url(row["id"])
        pay_req = PhonePePayRequest(
            merchant_order_id=row["order_id"],
            amount_paisa=amount_paisa,
            redirect_url=redirect,
            expire_after=get_phonepe_config().order_expire_seconds,
            meta_info={
                "udf1": row["id"],
                "udf2": user_id,
                "udf3": plan_id,
            },
        )
        try:
            pp_resp = self._phonepe.create_payment(pay_req)
        except Exception as exc:
            self._repo.fail_payment(row["id"], user_id)
            logger.error("phonepe_create_order_failed payment_id=%s error=%s", row["id"], exc)
            raise ValueError(f"Unable to initiate PhonePe payment: {exc}") from exc

        updated = self._repo.update_payment_gateway(
            row["id"],
            user_id,
            status="initiated",
            phonepe_order_id=pp_resp.order_id,
            merchant_transaction_id=row["order_id"],
            checkout_url=pp_resp.redirect_url,
        )
        log_payment_redirect_generated(user_id, row["order_id"], self.name)
        log_payment_started(user_id, row["order_id"])
        return self._to_record(updated)

    def get_order(self, user_id: str, order_id: str) -> Optional[OrderRecord]:
        row = self._repo.get_payment(order_id, user_id)
        return self._to_record(row) if row else None

    def sync_order_status(self, user_id: str, payment_id: str) -> OrderRecord:
        """Poll PhonePe and update local order — does NOT activate license."""
        row = self._repo.get_payment(payment_id, user_id)
        if not row:
            raise ValueError("Payment not found")
        if row["status"] in TERMINAL_STATUSES:
            return self._to_record(row)

        status = self._phonepe.get_order_status(row["order_id"])
        return self._apply_phonepe_status(row, status.state, status.transaction_id, status.payment_mode)

    def verify_payment(self, user_id: str, order_id: str, transaction_id: Optional[str] = None) -> OrderRecord:
        """Sync status only — license activation happens exclusively via webhook."""
        return self.sync_order_status(user_id, order_id)

    def _apply_phonepe_status(
        self,
        row: dict,
        phonepe_state: str,
        txn_id: Optional[str],
        payment_mode: Optional[str],
    ) -> OrderRecord:
        user_id = row["user_id"]
        payment_id = row["id"]
        state = phonepe_state.upper()

        if state == "COMPLETED":
            self._repo.complete_payment(
                payment_id,
                user_id,
                phonepe_transaction_id=txn_id,
                payment_method=payment_mode,
            )
            updated = self._repo.get_payment(payment_id, user_id)
            log_payment_success(user_id, row["order_id"], txn_id or "")
            return self._to_record(updated)  # type: ignore[arg-type]

        if state == "FAILED":
            self._repo.fail_payment(payment_id, user_id, phonepe_transaction_id=txn_id, payment_method=payment_mode)
            updated = self._repo.get_payment(payment_id, user_id)
            log_payment_failure(user_id, row["order_id"], "failed")
            return self._to_record(updated)  # type: ignore[arg-type]

        if state == "PENDING":
            updated = self._repo.update_payment_gateway(
                payment_id, user_id, status="processing",
                phonepe_transaction_id=txn_id, payment_method=payment_mode,
            )
            return self._to_record(updated)

        updated = self._repo.get_payment(payment_id, user_id)
        return self._to_record(updated)  # type: ignore[arg-type]

    def cancel(self, user_id: str, order_id: str) -> OrderRecord:
        self._repo.cancel_payment(order_id, user_id)
        row = self._repo.get_payment(order_id, user_id)
        if not row:
            raise ValueError("Order not found")
        log_payment_failure(user_id, row["order_id"], "cancelled")
        return self._to_record(row)

    def fail(self, user_id: str, order_id: str) -> OrderRecord:
        self._repo.fail_payment(order_id, user_id)
        row = self._repo.get_payment(order_id, user_id)
        if not row:
            raise ValueError("Order not found")
        log_payment_failure(user_id, row["order_id"], "failed")
        return self._to_record(row)

    def refund(self, user_id: str, order_id: str) -> OrderRecord:
        self._repo.refund_payment(order_id, user_id)
        row = self._repo.get_payment(order_id, user_id)
        if not row:
            raise ValueError("Order not found")
        return self._to_record(row)

    def webhook(self, payload: dict, authorization: Optional[str] = None) -> Optional[OrderRecord]:
        from inspectiq.payment.phonepe.webhook import verify_webhook_authorization

        if not verify_webhook_authorization(authorization):
            log_webhook_verification_failed()
            logger.warning("phonepe_webhook_verification_failed")
            raise ValueError("Invalid webhook authorization")

        event, inner = parse_webhook_event(payload)
        merchant_order_id = inner.get("merchantOrderId") or inner.get("originalMerchantOrderId") or ""
        log_webhook_received(event, str(merchant_order_id))
        event_key = webhook_event_id(event, inner)
        if self._repo.is_webhook_processed(event_key):
            logger.info("phonepe_webhook_duplicate event=%s", event_key)
            return None

        merchant_order_id = inner.get("merchantOrderId") or inner.get("originalMerchantOrderId")
        if not merchant_order_id:
            logger.warning("phonepe_webhook_missing_merchant_order_id event=%s", event)
            return None

        row = self._repo.get_payment_by_merchant_order_id(str(merchant_order_id))
        if not row:
            logger.warning("phonepe_webhook_unknown_order merchant_order_id=%s", merchant_order_id)
            return None

        logger.info("phonepe_webhook_received event=%s order=%s", event, merchant_order_id)
        log_webhook_verification_passed(event, str(merchant_order_id))

        payment_mode = None
        txn_id = None
        details = inner.get("paymentDetails") or []
        if details:
            latest = details[-1]
            payment_mode = latest.get("paymentMode")
            txn_id = latest.get("transactionId")

        state = str(inner.get("state", "")).upper()
        record = self._apply_phonepe_status(row, state, txn_id, payment_mode)

        if event == "checkout.order.completed" and state == "COMPLETED":
            self._on_payment_success(row)
        elif event in ("checkout.order.failed",) or state == "FAILED":
            pass
        elif event == "pg.refund.completed":
            self._repo.refund_payment(row["id"], row["user_id"])
            log_refund_processed(row["user_id"], row["order_id"])
            record = self._to_record(self._repo.get_payment(row["id"], row["user_id"]))  # type: ignore[arg-type]

        self._repo.mark_webhook_processed(event_key, row["id"])
        return record

    def _on_payment_success(self, row: dict) -> None:
        from inspectiq.auth.services import LicenseService

        if row["status"] != "completed":
            refreshed = self._repo.get_payment(row["id"], row["user_id"])
            if refreshed and refreshed["status"] != "completed":
                return
        lic = LicenseService(self._repo)
        try:
            current = lic.get_license(row["user_id"])
            if current.status.value == "lifetime":
                return
        except ValueError:
            pass
        lic.activate_plan(row["user_id"], row["plan_id"], payment_ref=row["id"])
