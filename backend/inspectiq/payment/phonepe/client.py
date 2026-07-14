"""PhonePe Payment Gateway v2 API client."""

from __future__ import annotations

import time
from typing import Any, Optional
from urllib.parse import urlencode

import httpx

from inspectiq.logging_config import get_logger
from inspectiq.payment.phonepe.config import PhonePeConfig, get_phonepe_config
from inspectiq.payment.phonepe.dto import PhonePeOrderStatus, PhonePePayRequest, PhonePePayResponse

logger = get_logger("droidlens.payment.phonepe")

_token_cache: dict[str, Any] = {"token": None, "expires_at": 0}


class PhonePeService:
    """Low-level PhonePe PG v2 client — auth, pay, order status."""

    def __init__(self, config: Optional[PhonePeConfig] = None):
        self._cfg = config or get_phonepe_config()

    def _ensure_configured(self) -> None:
        if not self._cfg.configured:
            raise ValueError(
                "PhonePe is not configured. Set PHONEPE_CLIENT_ID, PHONEPE_CLIENT_SECRET, "
                "PHONEPE_CLIENT_VERSION, and PHONEPE_CALLBACK_URL."
            )

    def get_access_token(self) -> str:
        self._ensure_configured()
        now = int(time.time())
        cached = _token_cache.get("token")
        expires_at = int(_token_cache.get("expires_at") or 0)
        if cached and now < expires_at - 60:
            return str(cached)

        data = urlencode({
            "client_id": self._cfg.client_id,
            "client_version": self._cfg.client_version,
            "client_secret": self._cfg.client_secret,
            "grant_type": "client_credentials",
        })
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(
                self._cfg.auth_url,
                content=data,
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Accept": "application/json",
                },
            )
            resp.raise_for_status()
            body = resp.json()

        token = body["access_token"]
        exp = int(body.get("expires_at") or (now + 3600))
        _token_cache["token"] = token
        _token_cache["expires_at"] = exp
        logger.info("phonepe_auth_token_refreshed expires_at=%s", exp)
        return token

    def _auth_headers(self) -> dict[str, str]:
        token = self.get_access_token()
        return {
            "Authorization": f"O-Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def create_payment(self, req: PhonePePayRequest) -> PhonePePayResponse:
        self._ensure_configured()
        payload = {
            "merchantOrderId": req.merchant_order_id,
            "amount": req.amount_paisa,
            "expireAfter": req.expire_after,
            "paymentFlow": {
                "type": "PG_CHECKOUT",
                "merchantUrls": {"redirectUrl": req.redirect_url},
            },
            "metaInfo": req.meta_info,
        }
        logger.info(
            "phonepe_payment_initiated merchant_order_id=%s amount_paisa=%s",
            req.merchant_order_id,
            req.amount_paisa,
        )
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(self._cfg.pay_url, json=payload, headers=self._auth_headers())
            if resp.status_code >= 400:
                logger.error("phonepe_pay_failed status=%s body=%s", resp.status_code, resp.text)
                resp.raise_for_status()
            body = resp.json()

        redirect = body.get("redirectUrl") or body.get("redirect_url")
        if not redirect:
            raise ValueError("PhonePe did not return a redirect URL")

        logger.info(
            "phonepe_redirect_generated merchant_order_id=%s phonepe_order_id=%s",
            req.merchant_order_id,
            body.get("orderId"),
        )
        return PhonePePayResponse(
            order_id=str(body.get("orderId", "")),
            state=str(body.get("state", "PENDING")),
            redirect_url=str(redirect),
            expire_at=body.get("expireAt"),
        )

    def get_order_status(self, merchant_order_id: str) -> PhonePeOrderStatus:
        self._ensure_configured()
        url = self._cfg.order_status_url(merchant_order_id)
        params = {"details": "false", "errorContext": "true"}
        headers = self._auth_headers()
        if self._cfg.merchant_id:
            headers["X-MERCHANT-ID"] = self._cfg.merchant_id

        with httpx.Client(timeout=30.0) as client:
            resp = client.get(url, params=params, headers=headers)
            resp.raise_for_status()
            body = resp.json()

        payment_mode = None
        transaction_id = None
        details = body.get("paymentDetails") or []
        if details:
            latest = details[-1]
            payment_mode = latest.get("paymentMode")
            transaction_id = latest.get("transactionId")

        return PhonePeOrderStatus(
            order_id=str(body.get("orderId", "")),
            merchant_order_id=str(body.get("merchantOrderId", merchant_order_id)),
            state=str(body.get("state", "PENDING")),
            amount_paisa=int(body.get("amount") or 0),
            payment_mode=payment_mode,
            transaction_id=transaction_id,
            raw=body,
        )
