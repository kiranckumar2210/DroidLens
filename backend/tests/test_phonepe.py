"""PhonePe payment provider integration tests."""

from __future__ import annotations

import hashlib
import os
from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from inspectiq.api.main import app
from inspectiq.auth import dependencies
from inspectiq.auth.repository import create_auth_repository
from inspectiq.payment.phonepe.dto import PhonePeOrderStatus, PhonePePayResponse
from inspectiq.payment.phonepe.webhook import compute_webhook_authorization

TEST_PASSWORD = "SecurePass1"


@pytest.fixture
def phonepe_env(monkeypatch, tmp_path, paid_licensing_mode):
    monkeypatch.setenv("DROIDLENS_PAYMENT_PROVIDER", "phonepe")
    monkeypatch.setenv("PHONEPE_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("PHONEPE_CLIENT_SECRET", "test-client-secret")
    monkeypatch.setenv("PHONEPE_CLIENT_VERSION", "1")
    monkeypatch.setenv("PHONEPE_WEBHOOK_USERNAME", "wh-user")
    monkeypatch.setenv("PHONEPE_WEBHOOK_SECRET", "wh-pass")
    monkeypatch.setenv("PHONEPE_CALLBACK_URL", "http://test/return?payment_return=1")
    monkeypatch.setenv("PHONEPE_ENVIRONMENT", "sandbox")

    from inspectiq.auth.config import get_auth_config
    from inspectiq.payment.phonepe.config import get_phonepe_config

    get_auth_config.cache_clear()
    get_phonepe_config.cache_clear()

    db = str(tmp_path / "phonepe_auth.db")
    repo = create_auth_repository(db_path=db)
    dependencies.configure_for_testing(repo)
    from inspectiq.auth.system_settings_models import SystemSettingsUpdate
    from inspectiq.auth.system_settings_service import get_system_settings_service

    get_system_settings_service().update_settings(
        SystemSettingsUpdate(
            subscription_enabled=True,
            payment_enabled=True,
            trial_enabled=True,
        )
    )

    yield repo

    get_auth_config.cache_clear()
    get_phonepe_config.cache_clear()


@pytest.fixture
async def phonepe_client(phonepe_env):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


async def _register(client: AsyncClient, email: str = "phonepe@example.com") -> dict:
    r = await client.post(
        "/register",
        json={
            "full_name": "PhonePe User",
            "email": email,
            "password": TEST_PASSWORD,
            "confirm_password": TEST_PASSWORD,
        },
    )
    assert r.status_code == 200, r.text
    return r.json()["session"]


@pytest.mark.asyncio
@patch("inspectiq.payment.phonepe.client.PhonePeService.create_payment")
async def test_phonepe_create_order_returns_checkout_url(mock_pay, phonepe_client):
    mock_pay.return_value = PhonePePayResponse(
        order_id="PP-ORDER-1",
        state="PENDING",
        redirect_url="https://mercury-uat.phonepe.com/transact/uat?token=abc",
    )

    session = await _register(phonepe_client)
    token = session["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    purchase = await phonepe_client.post(
        "/payment/create-order",
        json={"plan_id": "lifetime"},
        headers=headers,
    )
    assert purchase.status_code == 200, purchase.text
    body = purchase.json()
    assert body["payment_provider"] == "phonepe"
    assert body["checkout_url"].startswith("https://")
    assert body["status"] == "initiated"
    assert body["amount_inr"] == 199


@pytest.mark.asyncio
@patch("inspectiq.payment.phonepe.client.PhonePeService.get_order_status")
@patch("inspectiq.payment.phonepe.client.PhonePeService.create_payment")
async def test_phonepe_verify_does_not_activate_without_webhook(mock_pay, mock_status, phonepe_client):
    mock_pay.return_value = PhonePePayResponse(
        order_id="PP-ORDER-2",
        state="PENDING",
        redirect_url="https://mercury-uat.phonepe.com/transact/uat?token=xyz",
    )
    mock_status.return_value = PhonePeOrderStatus(
        order_id="PP-ORDER-2",
        merchant_order_id="ORD-TEST",
        state="COMPLETED",
        amount_paisa=19900,
        payment_mode="UPI",
        transaction_id="TXN-PHONEPE-1",
    )

    session = await _register(phonepe_client, "sync@example.com")
    token = session["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    purchase = await phonepe_client.post(
        "/payment/create-order",
        json={"plan_id": "lifetime"},
        headers=headers,
    )
    payment_id = purchase.json()["payment_id"]

    verify = await phonepe_client.post(
        "/payment/verify",
        json={"payment_id": payment_id},
        headers=headers,
    )
    assert verify.status_code == 200
    assert verify.json()["status"] == "completed"
    assert verify.json()["license"]["status"] != "lifetime"

    profile = await phonepe_client.get("/profile", headers=headers)
    assert profile.json()["license"]["status"] != "lifetime"


@pytest.mark.asyncio
@patch("inspectiq.payment.phonepe.client.PhonePeService.create_payment")
async def test_phonepe_webhook_activates_lifetime(mock_pay, phonepe_client, phonepe_env):
    mock_pay.return_value = PhonePePayResponse(
        order_id="PP-ORDER-3",
        state="PENDING",
        redirect_url="https://mercury-uat.phonepe.com/transact/uat?token=wh",
    )

    session = await _register(phonepe_client, "webhook@example.com")
    token = session["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    purchase = await phonepe_client.post(
        "/payment/create-order",
        json={"plan_id": "lifetime"},
        headers=headers,
    )
    order_id = purchase.json()["order_id"]

    auth_header = compute_webhook_authorization("wh-user", "wh-pass")
    payload = {
        "event": "checkout.order.completed",
        "payload": {
            "merchantOrderId": order_id,
            "orderId": "PP-ORDER-3",
            "state": "COMPLETED",
            "paymentDetails": [{"transactionId": "TXN-WH-1", "paymentMode": "UPI"}],
        },
    }

    wh = await phonepe_client.post(
        "/payment/webhook",
        json=payload,
        headers={"Authorization": auth_header},
    )
    assert wh.status_code == 200
    assert wh.json()["status"] == "processed"

    profile = await phonepe_client.get("/profile", headers=headers)
    assert profile.json()["license"]["status"] == "lifetime"
    assert profile.json()["license"]["has_premium"] is True


@pytest.mark.asyncio
async def test_phonepe_webhook_rejects_invalid_signature(phonepe_client):
    payload = {
        "event": "checkout.order.completed",
        "payload": {"merchantOrderId": "ORD-FAKE", "state": "COMPLETED"},
    }
    wh = await phonepe_client.post(
        "/payment/webhook",
        json=payload,
        headers={"Authorization": "invalid-signature"},
    )
    assert wh.status_code == 401


def test_webhook_authorization_hash():
    expected = hashlib.sha256(b"user:pass").hexdigest()
    assert compute_webhook_authorization("user", "pass") == expected
