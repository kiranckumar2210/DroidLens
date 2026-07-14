"""Smart Interaction Recorder tests."""

import pytest
from httpx import ASGITransport, AsyncClient

from inspectiq.api.main import app
from inspectiq.auth import dependencies
from inspectiq.auth.repository import create_auth_repository
from inspectiq.auth.services import AuthService, LicenseService, PaymentService, UserService
from inspectiq.recording.engine import SmartRecordingEngine
from inspectiq.recording.models import RecordedActionType, RecordingSettings
from inspectiq.recording.optimizer import RecordingOptimizer
from inspectiq.recording.code_generation import DefaultCodeGenerationService
from inspectiq.recording.models import RecordedStep, RecordingSession, utcnow
import uuid

TEST_PASSWORD = "SecurePass1"


@pytest.fixture
async def premium_client(tmp_path):
    db = str(tmp_path / "test_auth.db")
    repo = create_auth_repository(db_path=db)
    dependencies.configure_for_testing(repo)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


async def _token(client: AsyncClient) -> str:
    r = await client.post(
        "/register",
        json={
            "full_name": "Recorder User",
            "email": "recorder@example.com",
            "password": TEST_PASSWORD,
            "confirm_password": TEST_PASSWORD,
        },
    )
    assert r.status_code == 200
    return r.json()["session"]["access_token"]


@pytest.mark.asyncio
async def test_recording_requires_premium(premium_client):
    r = await premium_client.post("/recording/start", json={"device_id": "emulator-5554"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_code_generation_assembles_script():
    gen = DefaultCodeGenerationService()
    settings = RecordingSettings(language_profile="python_uiautomator2")
    step = RecordedStep(
        id="s1",
        step_number=1,
        timestamp=utcnow(),
        action_type=RecordedActionType.PRESS_BACK,
        code_snippet="d.press('back')",
    )
    session = RecordingSession(id="sess", device_id="dev", settings=settings, steps=[step])
    script = gen.assemble_script(session)
    assert "d.press('back')" in script
    assert "uiautomator2" in script


@pytest.mark.asyncio
async def test_optimizer_dedupes_waits():
    opt = RecordingOptimizer()
    settings = RecordingSettings()
    steps = [
        RecordedStep(id="1", step_number=1, timestamp=utcnow(), action_type=RecordedActionType.WAIT, code_snippet="wait1"),
        RecordedStep(id="2", step_number=2, timestamp=utcnow(), action_type=RecordedActionType.WAIT, code_snippet="wait1"),
        RecordedStep(id="3", step_number=3, timestamp=utcnow(), action_type=RecordedActionType.TAP, code_snippet="click"),
    ]
    session = RecordingSession(id="s", device_id="d", settings=settings, steps=steps)
    result = opt.optimize(session)
    assert len(result.steps) == 2


def test_recording_engine_undo_redo():
    from inspectiq.recording.session_manager import InMemoryRecordingSessionManager
    engine = SmartRecordingEngine(session_manager=InMemoryRecordingSessionManager())
    session = engine._sessions.create("device-1")
    session.state = __import__("inspectiq.recording.models", fromlist=["RecordingState"]).RecordingState.RECORDING
    engine._snapshot_undo(session)
    session.steps.append(RecordedStep(
        id="a", step_number=1, timestamp=utcnow(), action_type=RecordedActionType.TAP, code_snippet="tap",
    ))
    engine._sessions.save(session)
    engine.undo(session.id)
    assert len(engine.get_session(session.id).steps) == 0
    engine.redo(session.id)
    assert len(engine.get_session(session.id).steps) == 1
