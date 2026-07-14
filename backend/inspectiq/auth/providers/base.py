"""Pluggable payment provider interface — swap Mock / Razorpay / Stripe without UI changes."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class OrderRecord:
    id: str
    user_id: str
    order_id: str
    transaction_id: str
    plan_id: str
    amount: int
    currency: str
    status: str
    payment_provider: str
    created_at: Any = None
    completed_at: Any = None
    checkout_url: Optional[str] = None
    payment_method: Optional[str] = None
    phonepe_order_id: Optional[str] = None
    phonepe_transaction_id: Optional[str] = None
    merchant_transaction_id: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "payment_id": self.id,
            "user_id": self.user_id,
            "order_id": self.order_id,
            "transaction_id": self.transaction_id,
            "plan_id": self.plan_id,
            "amount_inr": self.amount,
            "amount": self.amount,
            "currency": self.currency,
            "status": self.status,
            "payment_provider": self.payment_provider,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "checkout_url": self.checkout_url,
            "payment_method": self.payment_method,
            "phonepe_order_id": self.phonepe_order_id,
            "phonepe_transaction_id": self.phonepe_transaction_id,
            "merchant_transaction_id": self.merchant_transaction_id,
        }


class PaymentProvider(ABC):
    """Gateway-agnostic payment contract."""

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    def create_order(self, user_id: str, plan_id: str, amount: int, currency: str) -> OrderRecord:
        ...

    @abstractmethod
    def verify_payment(self, user_id: str, order_id: str, transaction_id: Optional[str] = None) -> OrderRecord:
        ...

    @abstractmethod
    def cancel(self, user_id: str, order_id: str) -> OrderRecord:
        ...

    @abstractmethod
    def fail(self, user_id: str, order_id: str) -> OrderRecord:
        ...

    @abstractmethod
    def refund(self, user_id: str, order_id: str) -> OrderRecord:
        ...

    @abstractmethod
    def webhook(self, payload: dict, authorization: Optional[str] = None) -> Optional[OrderRecord]:
        ...

    @abstractmethod
    def get_order(self, user_id: str, order_id: str) -> Optional[OrderRecord]:
        ...
