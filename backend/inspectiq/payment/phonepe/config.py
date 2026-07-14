"""PhonePe Payment Gateway configuration — all secrets from environment."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class PhonePeConfig:
    merchant_id: str
    client_id: str
    client_secret: str
    client_version: str
    environment: str  # sandbox | production
    callback_url: str
    webhook_username: str
    webhook_password: str
    order_expire_seconds: int = 1200

    @property
    def is_sandbox(self) -> bool:
        return self.environment.lower() in ("sandbox", "uat", "test")

    @property
    def auth_url(self) -> str:
        if self.is_sandbox:
            return "https://api-preprod.phonepe.com/apis/pg-sandbox/v1/oauth/token"
        return "https://api.phonepe.com/apis/identity-manager/v1/oauth/token"

    @property
    def pay_url(self) -> str:
        if self.is_sandbox:
            return "https://api-preprod.phonepe.com/apis/pg-sandbox/checkout/v2/pay"
        return "https://api.phonepe.com/apis/pg/checkout/v2/pay"

    def order_status_url(self, merchant_order_id: str) -> str:
        base = (
            "https://api-preprod.phonepe.com/apis/pg-sandbox"
            if self.is_sandbox
            else "https://api.phonepe.com/apis/pg"
        )
        return f"{base}/checkout/v2/order/{merchant_order_id}/status"

    @property
    def configured(self) -> bool:
        return bool(
            self.client_id and self.client_secret and self.client_version and self.callback_url
        )


@lru_cache
def get_phonepe_config() -> PhonePeConfig:
    env = os.environ.get("PHONEPE_ENVIRONMENT", os.environ.get("DROIDLENS_PHONEPE_ENV", "sandbox"))
    return PhonePeConfig(
        merchant_id=os.environ.get("PHONEPE_MERCHANT_ID", ""),
        client_id=os.environ.get("PHONEPE_CLIENT_ID", ""),
        client_secret=os.environ.get("PHONEPE_CLIENT_SECRET", ""),
        client_version=os.environ.get("PHONEPE_CLIENT_VERSION", "1"),
        environment=env,
        callback_url=os.environ.get(
            "PHONEPE_CALLBACK_URL",
            os.environ.get("DROIDLENS_PUBLIC_URL", "http://127.0.0.1:5173") + "/?payment_return=1",
        ),
        webhook_username=os.environ.get("PHONEPE_WEBHOOK_USERNAME", ""),
        webhook_password=os.environ.get("PHONEPE_WEBHOOK_SECRET", os.environ.get("PHONEPE_WEBHOOK_PASSWORD", "")),
        order_expire_seconds=int(os.environ.get("PHONEPE_ORDER_EXPIRE_SECONDS", "1200")),
    )
