"""v2.0 platform tests — mock sessions and platform detection."""

import pytest
from httpx import ASGITransport, AsyncClient

from inspectiq.api.main import app
from inspectiq.domain.models import Platform
from inspectiq.services.inspection_service import InspectionService


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_mock_session_ios(client):
    r = await client.post("/session/mock?platform=ios")
    assert r.status_code == 200
    data = r.json()
    assert data["platform"] == "ios"
    assert data["device_id"] == "mock-ios-001"
    assert "XCUIElementType" in (data.get("raw_xml") or "")


@pytest.mark.asyncio
async def test_mock_session_harmonyos(client):
    r = await client.post("/session/mock?platform=harmonyos")
    assert r.status_code == 200
    data = r.json()
    assert data["platform"] == "harmonyos"
    assert data["device_id"] == "mock-harmonyos-001"


@pytest.mark.asyncio
async def test_platform_status(client):
    r = await client.get("/platform/status")
    assert r.status_code == 200
    data = r.json()
    assert "platforms" in data
    assert "android" in data["platforms"]
    assert "ios" in data["platforms"]
    assert "harmonyos" in data["platforms"]
    assert "cloud" in data["platforms"]


def test_detect_platform_from_xml():
    svc = InspectionService()
    assert svc.detect_platform_from_xml("<XCUIElementTypeApplication/>") == Platform.IOS
    assert svc.detect_platform_from_xml("<hierarchy/>") == Platform.ANDROID


def test_is_valid_ui_xml_ios():
    assert InspectionService.is_valid_ui_xml("<XCUIElementTypeApplication/>", Platform.IOS)
    assert not InspectionService.is_valid_ui_xml("", Platform.IOS)


@pytest.mark.asyncio
async def test_list_devices_ios(client):
    r = await client.get("/devices?platform=ios")
    assert r.status_code == 200
    assert "devices" in r.json()
