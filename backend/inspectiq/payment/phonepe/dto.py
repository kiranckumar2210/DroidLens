"""PhonePe API request/response shapes (v2 Standard Checkout)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class PhonePePayRequest:
    merchant_order_id: str
    amount_paisa: int
    redirect_url: str
    expire_after: int = 1200
    meta_info: dict[str, str] = field(default_factory=dict)


@dataclass
class PhonePePayResponse:
    order_id: str
    state: str
    redirect_url: str
    expire_at: Optional[int] = None


@dataclass
class PhonePeOrderStatus:
    order_id: str
    merchant_order_id: str
    state: str
    amount_paisa: int
    payment_mode: Optional[str] = None
    transaction_id: Optional[str] = None
    raw: dict[str, Any] = field(default_factory=dict)
