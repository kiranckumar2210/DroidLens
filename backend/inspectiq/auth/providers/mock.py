"""Mock payment provider for development and QA."""

from __future__ import annotations

from typing import Any, Optional

from inspectiq.auth.audit_log import (
    log_order_created,
    log_payment_failure,
    log_payment_started,
    log_payment_success,
)
from inspectiq.auth.config import get_auth_config
from inspectiq.auth.providers.base import OrderRecord, PaymentProvider


class MockPaymentProvider(PaymentProvider):
    def __init__(self, repo: Any):
        self._repo = repo

    @property
    def name(self) -> str:
        return "mock"

    def _to_record(self, row: dict) -> OrderRecord:
        return OrderRecord(
            id=row["id"],
            user_id=row["user_id"],
            order_id=row["order_id"],
            transaction_id=row["transaction_id"],
            plan_id=row["plan_id"],
            amount=row.get("amount_inr") or row.get("amount", 0),
            currency=row.get("currency", get_auth_config().currency),
            status=row["status"],
            payment_provider=row.get("payment_provider", self.name),
            created_at=row.get("created_at"),
            completed_at=row.get("completed_at"),
        )

    def create_order(self, user_id: str, plan_id: str, amount: int, currency: str) -> OrderRecord:
        existing = self._repo.get_pending_payment(user_id)
        if existing:
            record = self._to_record(existing)
            log_payment_started(user_id, record.order_id)
            return record
        row = self._repo.create_payment(
            user_id, plan_id, amount,
            currency=currency,
            payment_provider=self.name,
        )
        record = self._to_record(row)
        log_order_created(user_id, record.order_id, amount, self.name)
        log_payment_started(user_id, record.order_id)
        return record

    def get_order(self, user_id: str, order_id: str) -> Optional[OrderRecord]:
        row = self._repo.get_payment(order_id, user_id)
        return self._to_record(row) if row else None

    def verify_payment(self, user_id: str, order_id: str, transaction_id: Optional[str] = None) -> OrderRecord:
        self._repo.complete_payment(order_id, user_id)
        row = self._repo.get_payment(order_id, user_id)
        if not row:
            raise ValueError("Order not found after verification")
        record = self._to_record(row)
        log_payment_success(user_id, record.order_id, record.transaction_id)
        return record

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
        """Mock webhooks are not used — real providers implement signature verification."""
        return None
