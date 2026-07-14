"""System settings and licensing management tests."""

import os

import pytest
from httpx import ASGITransport, AsyncClient

from inspectiq.api.main import app
from inspectiq.auth import dependencies
from inspectiq.auth.repository import create_auth_repository
from inspectiq.auth.system_settings_service import get_system_settings_service

TEST_PASSWORD = "SecurePass1"
ADMIN_EMAIL = "admin@example.com"
USER_EMAIL = "user@example.com"


@pytest.fixture
async def settings_client(tmp_path, monkeypatch):
    monkeypatch.setenv("DROIDLENS_ADMIN_EMAIL", ADMIN_EMAIL)
    from inspectiq.auth.config import get_auth_config
    get_auth_config.cache_clear()

    db = str(tmp_path / "test_settings.db")
    repo = create_auth_repository(db_path=db)
    dependencies.configure_for_testing(repo)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, repo

    get_auth_config.cache_clear()
    get_system_settings_service().invalidate_cache()


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


async def _login(client: AsyncClient, email: str) -> str:
    r = await client.post("/login", json={"email": email, "password": TEST_PASSWORD})
    assert r.status_code == 200, r.text
    return r.json()["session"]["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_public_system_config_no_auth(settings_client):
    client, _repo = settings_client
    r = await client.get("/auth/system-config")
    assert r.status_code == 200
    data = r.json()
    assert data["subscription_enabled"] is False
    assert data["payment_enabled"] is True
    assert data["trial_enabled"] is True
    assert data["guest_access_enabled"] is True
    assert "features" in data
    assert data["features"]["live_inspector"] is True


@pytest.mark.asyncio
async def test_new_user_gets_lifetime_when_subscription_disabled(settings_client):
    client, _repo = settings_client
    session = await _register(client, USER_EMAIL)
    assert session["license"]["status"] == "lifetime"
    assert session["license"]["has_premium"] is True


@pytest.mark.asyncio
async def test_admin_can_get_and_update_settings(settings_client):
    client, _repo = settings_client
    await _register(client, ADMIN_EMAIL, "Admin")
    token = await _login(client, ADMIN_EMAIL)

    r = await client.get("/admin/settings/licensing", headers=_auth(token))
    assert r.status_code == 200
    assert r.json()["subscription"]["subscription_enabled"] is False

    patch = await client.patch(
        "/admin/settings/licensing",
        headers=_auth(token),
        json={"subscription_enabled": True, "trial_days": 14},
    )
    assert patch.status_code == 200
    body = patch.json()
    assert body["subscription"]["subscription_enabled"] is True
    assert body["payment"]["trial_days"] == 14

    public = await client.get("/auth/system-config")
    assert public.json()["subscription_enabled"] is True
    assert public.json()["trial_days"] == 14


@pytest.mark.asyncio
async def test_non_admin_cannot_update_settings(settings_client):
    client, _repo = settings_client
    await _register(client, USER_EMAIL)
    token = await _login(client, USER_EMAIL)

    r = await client.patch(
        "/admin/settings/licensing",
        headers=_auth(token),
        json={"subscription_enabled": True},
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_premium_bypass_when_subscription_disabled(settings_client):
    client, _repo = settings_client
    session = await _register(client, USER_EMAIL)
    token = session["access_token"]

    r = await client.post(
        "/session/connect",
        headers=_auth(token),
        json={"device_id": "emulator-5554", "platform": "android"},
    )
    # May fail on device validation but should not be 403 for premium
    assert r.status_code != 403 or "premium" not in r.text.lower()


@pytest.mark.asyncio
async def test_payment_blocked_when_subscription_disabled(settings_client):
    client, _repo = settings_client
    session = await _register(client, USER_EMAIL)
    token = session["access_token"]

    r = await client.post(
        "/auth/purchase",
        headers=_auth(token),
        json={"plan_id": "lifetime"},
    )
    assert r.status_code == 400
    assert "disabled" in r.json()["detail"].lower()


@pytest.mark.asyncio
async def test_payment_blocked_when_payment_disabled(settings_client):
    client, _repo = settings_client
    await _register(client, ADMIN_EMAIL)
    admin_token = await _login(client, ADMIN_EMAIL)

    await client.patch(
        "/admin/settings/licensing",
        headers=_auth(admin_token),
        json={"subscription_enabled": True, "payment_enabled": False},
    )

    session = await _register(client, "buyer@example.com")
    token = session["access_token"]
    r = await client.post(
        "/auth/purchase",
        headers=_auth(token),
        json={"plan_id": "lifetime"},
    )
    assert r.status_code == 400
    assert "disabled" in r.json()["detail"].lower()


@pytest.mark.asyncio
async def test_admin_set_license_override(settings_client):
    client, _repo = settings_client
    await _register(client, ADMIN_EMAIL)
    user_session = await _register(client, USER_EMAIL)
    user_id = user_session["user"]["id"]
    admin_token = await _login(client, ADMIN_EMAIL)

    r = await client.post(
        f"/admin/users/{user_id}/set-license",
        headers=_auth(admin_token),
        json={"license_type": "expired"},
    )
    assert r.status_code == 200

    me = await client.get("/auth/me", headers=_auth(user_session["access_token"]))
    assert me.json()["license"]["status"] == "trial_expired"


@pytest.mark.asyncio
async def test_settings_change_audit_logged(settings_client):
    client, _repo = settings_client
    await _register(client, ADMIN_EMAIL)
    token = await _login(client, ADMIN_EMAIL)

    await client.patch(
        "/admin/settings/licensing",
        headers=_auth(token),
        json={"promotional_message": "Summer sale!"},
    )

    activity = await client.get("/admin/activity?action=settings_change", headers=_auth(token))
    assert activity.status_code == 200
    items = activity.json()["items"]
    assert any("promotional_message" in (e.get("detail") or "") for e in items)


@pytest.mark.asyncio
async def test_feature_flag_disables_endpoint(settings_client):
    client, _repo = settings_client
    await _register(client, ADMIN_EMAIL)
    admin_token = await _login(client, ADMIN_EMAIL)

    await client.patch(
        "/admin/settings/licensing",
        headers=_auth(admin_token),
        json={"live_inspector": False},
    )

    session = await _register(client, USER_EMAIL)
    token = session["access_token"]
    r = await client.post(
        "/session/connect",
        headers=_auth(token),
        json={"device_id": "emulator-5554", "platform": "android"},
    )
    assert r.status_code == 403
    assert "disabled" in r.json()["detail"].lower()
