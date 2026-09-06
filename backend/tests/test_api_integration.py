"""Integration tests with mock device."""

import pytest
from httpx import ASGITransport, AsyncClient

from inspectiq.api.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_health(client):
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json()["product"] == "DroidLens"


@pytest.mark.asyncio
async def test_list_devices_live_only(client):
    r = await client.get("/devices", params={"platform": "android"})
    assert r.status_code == 200
    body = r.json()
    assert "devices" in body
    assert body.get("live_only") is True
    for d in body["devices"]:
        assert not d["id"].startswith("mock-")


@pytest.mark.asyncio
async def test_mock_session_endpoint(client):
    r = await client.post("/session/mock")
    assert r.status_code == 200
    session = r.json()
    assert session["device_id"] == "mock-android-001"
    assert session["tree"] is not None
    assert session["screenshot_base64"]


@pytest.mark.asyncio
async def test_full_inspection_flow(client):
    session_resp = await client.post("/session/mock")
    assert session_resp.status_code == 200
    device_id = session_resp.json()["device_id"]

    inspect = await client.post(
        "/inspect/select",
        json={"device_id": device_id, "x": 500, "y": 750},
    )
    assert inspect.status_code == 200
    data = inspect.json()
    assert data["element"]["text"] == "Login"
    assert len(data["locators"]) > 0
    assert data["locators"][0]["scores"]["overall"] > 0

    # Code generation requires authentication
    script = await client.post(
        "/code/generate",
        json={
            "locator": data["locators"][0],
            "language": "python",
            "element_name": "login_button",
        },
    )
    assert script.status_code == 401


@pytest.mark.asyncio
async def test_live_connect_rejects_mock_device_id(client):
    r = await client.post(
        "/session/connect",
        json={"device_id": "mock-android-001", "platform": "android"},
    )
    assert r.status_code in (400, 401, 503)
    detail = r.json()["detail"].lower()
    assert "mock" in detail or "authentication" in detail
