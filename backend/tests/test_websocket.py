"""WebSocket live refresh integration tests."""

import os

import pytest
from fastapi.testclient import TestClient

from inspectiq.api.main import app

client = TestClient(app)


def test_websocket_rejects_mock_device_refresh():
    mock = client.post("/session/mock").json()
    device_id = mock["device_id"]

    with client.websocket_connect("/ws/live") as ws:
        ws.send_json({
            "action": "refresh_once",
            "device_id": device_id,
            "platform": "android",
        })
        msg = ws.receive_json()
        assert msg["type"] == "error"
        assert "mock" in msg["message"].lower()


@pytest.mark.skipif(
    os.environ.get("RUN_LIVE_TESTS") != "1",
    reason="Set RUN_LIVE_TESTS=1 to run WebSocket tests against a real device",
)
def test_websocket_subscribe_and_refresh_live():
    devices = client.get("/devices", params={"platform": "android"}).json()["devices"]
    device_id = devices[0]["id"]

    connect = client.post(
        "/session/connect",
        json={"device_id": device_id, "platform": "android"},
    )
    assert connect.status_code == 200
    assert connect.json()["mode"] == "live"

    with client.websocket_connect("/ws/live") as ws:
        ws.send_json({
            "action": "subscribe",
            "device_id": device_id,
            "platform": "android",
            "interval": 0.5,
        })
        msg = ws.receive_json()
        assert msg["type"] == "subscribed"
        assert msg["device_id"] == device_id

        update = ws.receive_json()
        assert update["type"] == "session_update"
        assert update["session"]["device_id"] == device_id
        assert update["session"]["mode"] == "live"
        assert update["session"]["tree"] is not None

        ws.send_json({"action": "unsubscribe"})
        unsub = ws.receive_json()
        assert unsub["type"] == "unsubscribed"
