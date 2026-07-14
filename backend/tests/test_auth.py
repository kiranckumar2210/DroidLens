"""Authentication, licensing, and payment security tests."""

import pytest
from httpx import ASGITransport, AsyncClient

from inspectiq.api.main import app
from inspectiq.auth import dependencies
from inspectiq.auth.repository import create_auth_repository

TEST_PASSWORD = "SecurePass1"


@pytest.fixture
async def auth_client(tmp_path):
    db = str(tmp_path / "test_auth.db")
    repo = create_auth_repository(db_path=db)
    dependencies.configure_for_testing(repo)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


async def _register(client: AsyncClient, email: str = "user@example.com") -> dict:
    r = await client.post(
        "/register",
        json={
            "full_name": "Test User",
            "email": email,
            "password": TEST_PASSWORD,
            "confirm_password": TEST_PASSWORD,
        },
    )
    assert r.status_code == 200, r.text
    return r.json()["session"]


@pytest.mark.asyncio
async def test_register_starts_trial(auth_client):
    session = await _register(auth_client)
    assert session["user"]["email"] == "user@example.com"
    assert session["license"]["status"] == "trial_active"
    assert session["license"]["has_premium"] is True
    assert session["license"]["days_remaining"] is not None
    assert session["access_token"]
    assert session["refresh_token"]


@pytest.mark.asyncio
async def test_register_duplicate_email(auth_client):
    await _register(auth_client)
    r = await auth_client.post(
        "/register",
        json={
            "full_name": "Another",
            "email": "user@example.com",
            "password": TEST_PASSWORD,
            "confirm_password": TEST_PASSWORD,
        },
    )
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_login_and_profile(auth_client):
    await _register(auth_client, "login@example.com")
    r = await auth_client.post(
        "/login",
        json={"email": "login@example.com", "password": TEST_PASSWORD, "remember_me": True},
    )
    assert r.status_code == 200
    token = r.json()["session"]["access_token"]
    refresh = r.json()["session"]["refresh_token"]

    profile = await auth_client.get("/profile", headers={"Authorization": f"Bearer {token}"})
    assert profile.status_code == 200
    body = profile.json()
    assert body["user"]["email"] == "login@example.com"
    assert body["license"]["has_premium"] is True

    refreshed = await auth_client.post("/refresh", json={"refresh_token": refresh})
    assert refreshed.status_code == 200
    assert refreshed.json()["session"]["access_token"]


@pytest.mark.asyncio
async def test_pricing(auth_client):
    r = await auth_client.get("/pricing")
    assert r.status_code == 200
    data = r.json()
    assert data["lifetime_price_inr"] == 199
    assert data["currency"] == "INR"


@pytest.mark.asyncio
async def test_premium_endpoint_requires_auth(auth_client):
    r = await auth_client.post(
        "/code/generate",
        json={
            "locator": {"locator_type": "xpath", "value": "//*", "scores": {}},
            "language": "python",
            "element_name": "btn",
        },
    )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_premium_endpoint_with_trial(auth_client):
    session = await _register(auth_client, "premium@example.com")
    token = session["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    mock = await auth_client.post("/session/mock")
    assert mock.status_code == 200
    device_id = mock.json()["device_id"]

    inspect = await auth_client.post(
        "/inspect/select",
        json={"device_id": device_id, "x": 500, "y": 750},
    )
    assert inspect.status_code == 200
    locator = inspect.json()["locators"][0]

    code = await auth_client.post(
        "/code/generate",
        json={"locator": locator, "language": "python", "element_name": "login_button"},
        headers=headers,
    )
    assert code.status_code == 200
    assert "code" in code.json()


@pytest.mark.asyncio
async def test_create_order_does_not_unlock_premium(auth_client):
    session = await _register(auth_client, "buyer@example.com")
    token = session["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    purchase = await auth_client.post(
        "/payment/create-order",
        json={"plan_id": "lifetime"},
        headers=headers,
    )
    assert purchase.status_code == 200
    body = purchase.json()
    assert body["status"] == "pending"
    assert body["order_id"].startswith("ORD-")
    assert body["transaction_id"].startswith("TXN-")
    assert body["amount_inr"] == 199

    profile = await auth_client.get("/profile", headers=headers)
    assert profile.status_code == 200
    lic = profile.json()["license"]
    assert lic["status"] != "lifetime"
    assert lic["has_premium"] is True


@pytest.mark.asyncio
async def test_lifetime_purchase_requires_success_confirmation(auth_client):
    session = await _register(auth_client, "confirm@example.com")
    token = session["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    purchase = await auth_client.post(
        "/payment/create-order",
        json={"plan_id": "lifetime"},
        headers=headers,
    )
    payment_id = purchase.json()["payment_id"]

    confirm = await auth_client.post(
        "/payment/verify",
        json={"payment_id": payment_id},
        headers=headers,
    )
    assert confirm.status_code == 200
    assert confirm.json()["status"] == "completed"
    assert confirm.json()["license"]["status"] == "lifetime"
    assert confirm.json()["license"]["has_premium"] is True


@pytest.mark.asyncio
async def test_failed_payment_does_not_unlock(auth_client):
    session = await _register(auth_client, "fail@example.com")
    token = session["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    purchase = await auth_client.post(
        "/payment/create-order",
        json={"plan_id": "lifetime"},
        headers=headers,
    )
    payment_id = purchase.json()["payment_id"]

    fail = await auth_client.post(
        "/payment/fail",
        json={"payment_id": payment_id},
        headers=headers,
    )
    assert fail.status_code == 200
    assert fail.json()["status"] == "failed"
    assert fail.json()["license"]["status"] != "lifetime"

    confirm = await auth_client.post(
        "/payment/verify",
        json={"payment_id": payment_id},
        headers=headers,
    )
    assert confirm.status_code == 400


@pytest.mark.asyncio
async def test_cancelled_payment_does_not_unlock(auth_client):
    session = await _register(auth_client, "cancel@example.com")
    token = session["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    purchase = await auth_client.post(
        "/payment/create-order",
        json={"plan_id": "lifetime"},
        headers=headers,
    )
    payment_id = purchase.json()["payment_id"]

    cancel = await auth_client.post(
        "/payment/cancel",
        json={"payment_id": payment_id},
        headers=headers,
    )
    assert cancel.status_code == 200
    assert cancel.json()["status"] == "cancelled"
    assert cancel.json()["license"]["status"] != "lifetime"


@pytest.mark.asyncio
async def test_list_plans(auth_client):
    r = await auth_client.get("/auth/plans")
    assert r.status_code == 200
    plans = r.json()
    ids = {p["id"] for p in plans}
    assert "trial" in ids
    assert "lifetime" in ids
    lifetime = next(p for p in plans if p["id"] == "lifetime")
    assert lifetime["price_inr"] == 199


@pytest.mark.asyncio
async def test_forgot_password_placeholder(auth_client):
    r = await auth_client.post("/forgot-password", json={"email": "nobody@example.com"})
    assert r.status_code == 200
    assert r.json()["status"] == "accepted"
