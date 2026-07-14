"""Admin dashboard API tests."""

import os

import pytest
from httpx import ASGITransport, AsyncClient

from inspectiq.api.main import app
from inspectiq.auth import dependencies
from inspectiq.auth.repository import create_auth_repository

TEST_PASSWORD = "SecurePass1"
ADMIN_EMAIL = "admin@example.com"
USER_EMAIL = "user@example.com"


@pytest.fixture
async def admin_client(tmp_path, monkeypatch):
    monkeypatch.setenv("DROIDLENS_ADMIN_EMAIL", ADMIN_EMAIL)
    from inspectiq.auth.config import get_auth_config
    get_auth_config.cache_clear()

    db = str(tmp_path / "test_admin.db")
    repo = create_auth_repository(db_path=db)
    dependencies.configure_for_testing(repo)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, repo

    get_auth_config.cache_clear()


async def _register(client: AsyncClient, email: str, name: str = "Test User") -> dict:
    r = await client.post(
        "/register",
        json={
            "full_name": name,
            "email": email,
            "password": TEST_PASSWORD,
            "confirm_password": TEST_PASSWORD,
        },
    )
    assert r.status_code == 200, r.text
    return r.json()["session"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_admin_email_gets_admin_role(admin_client):
    client, _repo = admin_client
    session = await _register(client, ADMIN_EMAIL, "Admin User")
    assert session["user"]["role"] == "admin"
    assert session["user"]["email"] == ADMIN_EMAIL


@pytest.mark.asyncio
async def test_regular_user_not_admin(admin_client):
    client, _repo = admin_client
    session = await _register(client, USER_EMAIL, "Regular User")
    assert session["user"]["role"] == "user"


@pytest.mark.asyncio
async def test_admin_endpoints_forbid_non_admin(admin_client):
    client, _repo = admin_client
    user_session = await _register(client, USER_EMAIL)
    token = user_session["access_token"]
    r = await client.get("/admin/dashboard", headers=_auth(token))
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_admin_endpoints_forbid_unauthenticated(admin_client):
    client, _repo = admin_client
    r = await client.get("/admin/dashboard")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_admin_dashboard_kpis(admin_client):
    client, _repo = admin_client
    await _register(client, ADMIN_EMAIL, "Admin")
    await _register(client, USER_EMAIL, "User One")
    await _register(client, "user2@example.com", "User Two")

    admin_login = await client.post(
        "/login",
        json={"email": ADMIN_EMAIL, "password": TEST_PASSWORD},
    )
    admin_token = admin_login.json()["session"]["access_token"]

    r = await client.get("/admin/dashboard", headers=_auth(admin_token))
    assert r.status_code == 200
    data = r.json()
    assert data["kpis"]["total_registered_users"] >= 3
    assert "registration" in data
    assert "revenue" in data
    assert "payments" in data
    assert "subscriptions" in data
    assert "recent_users" in data
    assert "recent_activity" in data


@pytest.mark.asyncio
async def test_admin_list_users_pagination(admin_client):
    client, _repo = admin_client
    await _register(client, ADMIN_EMAIL, "Admin")
    for i in range(5):
        await _register(client, f"paginated{i}@example.com", f"User {i}")

    admin_login = await client.post(
        "/login",
        json={"email": ADMIN_EMAIL, "password": TEST_PASSWORD},
    )
    token = admin_login.json()["session"]["access_token"]

    r = await client.get("/admin/users?page=1&page_size=3", headers=_auth(token))
    assert r.status_code == 200
    body = r.json()
    assert len(body["items"]) == 3
    assert body["total"] >= 6
    assert body["page"] == 1
    assert body["page_size"] == 3


@pytest.mark.asyncio
async def test_admin_user_search(admin_client):
    client, _repo = admin_client
    await _register(client, ADMIN_EMAIL, "Admin")
    await _register(client, "findme@example.com", "Findable Person")

    admin_login = await client.post(
        "/login",
        json={"email": ADMIN_EMAIL, "password": TEST_PASSWORD},
    )
    token = admin_login.json()["session"]["access_token"]

    r = await client.get("/admin/users?search=findme", headers=_auth(token))
    assert r.status_code == 200
    items = r.json()["items"]
    assert any(u["email"] == "findme@example.com" for u in items)


@pytest.mark.asyncio
async def test_admin_suspend_and_block_login(admin_client):
    client, _repo = admin_client
    await _register(client, ADMIN_EMAIL, "Admin")
    user_session = await _register(client, USER_EMAIL, "Suspend Me")
    user_id = user_session["user"]["id"]

    admin_login = await client.post(
        "/login",
        json={"email": ADMIN_EMAIL, "password": TEST_PASSWORD},
    )
    admin_token = admin_login.json()["session"]["access_token"]

    suspend = await client.post(f"/admin/users/{user_id}/suspend", headers=_auth(admin_token))
    assert suspend.status_code == 200
    assert suspend.json()["ok"] is True

    login = await client.post(
        "/login",
        json={"email": USER_EMAIL, "password": TEST_PASSWORD},
    )
    assert login.status_code == 401
    assert "suspended" in login.json()["detail"].lower()


@pytest.mark.asyncio
async def test_admin_reset_trial(admin_client):
    client, _repo = admin_client
    await _register(client, ADMIN_EMAIL, "Admin")
    user_session = await _register(client, USER_EMAIL, "Trial User")
    user_id = user_session["user"]["id"]

    admin_login = await client.post(
        "/login",
        json={"email": ADMIN_EMAIL, "password": TEST_PASSWORD},
    )
    token = admin_login.json()["session"]["access_token"]

    r = await client.post(f"/admin/users/{user_id}/reset-trial", headers=_auth(token))
    assert r.status_code == 200
    assert r.json()["ok"] is True

    detail = await client.get(f"/admin/users/{user_id}", headers=_auth(token))
    assert detail.status_code == 200
    assert detail.json()["license"]["status"] == "trial_active"


@pytest.mark.asyncio
async def test_admin_activate_license(admin_client):
    client, _repo = admin_client
    await _register(client, ADMIN_EMAIL, "Admin")
    user_session = await _register(client, USER_EMAIL, "License User")
    user_id = user_session["user"]["id"]

    admin_login = await client.post(
        "/login",
        json={"email": ADMIN_EMAIL, "password": TEST_PASSWORD},
    )
    token = admin_login.json()["session"]["access_token"]

    r = await client.post(f"/admin/users/{user_id}/activate-license", headers=_auth(token))
    assert r.status_code == 200

    detail = await client.get(f"/admin/users/{user_id}", headers=_auth(token))
    assert detail.json()["license"]["status"] == "lifetime"


@pytest.mark.asyncio
async def test_admin_delete_user(admin_client):
    client, _repo = admin_client
    await _register(client, ADMIN_EMAIL, "Admin")
    user_session = await _register(client, "delete@example.com", "Delete Me")
    user_id = user_session["user"]["id"]

    admin_login = await client.post(
        "/login",
        json={"email": ADMIN_EMAIL, "password": TEST_PASSWORD},
    )
    token = admin_login.json()["session"]["access_token"]

    r = await client.delete(f"/admin/users/{user_id}", headers=_auth(token))
    assert r.status_code == 200

    detail = await client.get(f"/admin/users/{user_id}", headers=_auth(token))
    assert detail.status_code == 404


@pytest.mark.asyncio
async def test_admin_payments_and_revenue(admin_client):
    client, _repo = admin_client
    await _register(client, ADMIN_EMAIL, "Admin")
    admin_login = await client.post(
        "/login",
        json={"email": ADMIN_EMAIL, "password": TEST_PASSWORD},
    )
    admin_token = admin_login.json()["session"]["access_token"]

    enable = await client.patch(
        "/admin/settings/licensing",
        headers=_auth(admin_token),
        json={"subscription_enabled": True},
    )
    assert enable.status_code == 200

    buyer = await _register(client, "buyer@example.com", "Buyer")
    token = buyer["access_token"]

    purchase = await client.post(
        "/payment/create-order",
        json={"plan_id": "lifetime"},
        headers=_auth(token),
    )
    assert purchase.status_code == 200, purchase.text
    payment_id = purchase.json()["payment_id"]
    await client.post(
        "/payment/verify",
        json={"payment_id": payment_id},
        headers=_auth(token),
    )

    payments = await client.get("/admin/payments", headers=_auth(admin_token))
    assert payments.status_code == 200
    assert payments.json()["total"] >= 1

    revenue = await client.get("/admin/revenue", headers=_auth(admin_token))
    assert revenue.status_code == 200
    assert revenue.json()["total_inr"] >= 199


@pytest.mark.asyncio
async def test_admin_activity_log(admin_client):
    client, _repo = admin_client
    await _register(client, ADMIN_EMAIL, "Admin")
    await _register(client, USER_EMAIL, "Activity User")

    admin_login = await client.post(
        "/login",
        json={"email": ADMIN_EMAIL, "password": TEST_PASSWORD},
    )
    token = admin_login.json()["session"]["access_token"]

    r = await client.get("/admin/activity", headers=_auth(token))
    assert r.status_code == 200
    body = r.json()
    assert body["total"] >= 1
    assert len(body["items"]) >= 1
    actions = {e["action"] for e in body["items"]}
    assert "registration" in actions or "login" in actions


@pytest.mark.asyncio
async def test_admin_csv_export(admin_client):
    client, _repo = admin_client
    await _register(client, ADMIN_EMAIL, "Admin")
    await _register(client, USER_EMAIL, "CSV User")

    admin_login = await client.post(
        "/login",
        json={"email": ADMIN_EMAIL, "password": TEST_PASSWORD},
    )
    token = admin_login.json()["session"]["access_token"]

    users_csv = await client.get("/admin/users/export", headers=_auth(token))
    assert users_csv.status_code == 200
    assert "email" in users_csv.text
    assert "text/csv" in users_csv.headers.get("content-type", "")

    payments_csv = await client.get("/admin/payments/export", headers=_auth(token))
    assert payments_csv.status_code == 200
    assert "order_id" in payments_csv.text


@pytest.mark.asyncio
async def test_admin_statistics_endpoint(admin_client):
    client, _repo = admin_client
    await _register(client, ADMIN_EMAIL, "Admin")

    admin_login = await client.post(
        "/login",
        json={"email": ADMIN_EMAIL, "password": TEST_PASSWORD},
    )
    token = admin_login.json()["session"]["access_token"]

    r = await client.get("/admin/statistics", headers=_auth(token))
    assert r.status_code == 200
    data = r.json()
    assert "registration" in data
    assert "kpis" in data


@pytest.mark.asyncio
async def test_admin_audit_on_suspend(admin_client):
    client, _repo = admin_client
    await _register(client, ADMIN_EMAIL, "Admin")
    user_session = await _register(client, USER_EMAIL, "Audit User")
    user_id = user_session["user"]["id"]

    admin_login = await client.post(
        "/login",
        json={"email": ADMIN_EMAIL, "password": TEST_PASSWORD},
    )
    token = admin_login.json()["session"]["access_token"]

    await client.post(f"/admin/users/{user_id}/suspend", headers=_auth(token))

    activity = await client.get("/admin/activity?action=admin_suspend_user", headers=_auth(token))
    assert activity.status_code == 200
    assert activity.json()["total"] >= 1
