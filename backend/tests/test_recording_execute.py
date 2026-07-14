"""Inspector-driven action execution tests."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from inspectiq.recording.engine import SmartRecordingEngine
from inspectiq.recording.models import RecordedActionType, RecordingState, StepExecutionStatus
from inspectiq.recording.session_manager import InMemoryRecordingSessionManager


@pytest.mark.asyncio
async def test_execute_and_record_does_not_use_getevent():
    """Recording is command-driven — no passive device monitor."""
    engine = SmartRecordingEngine(session_manager=InMemoryRecordingSessionManager())
    session = engine._sessions.create("device-1")
    session.state = RecordingState.RECORDING
    engine._sessions.save(session)

    mock_inspection = MagicMock()
    mock_inspection.inspect_element_by_id.return_value = None
    engine._inspection = mock_inspection
    engine._executor = AsyncMock()

    with patch.object(engine, "_resolve_inspection", return_value=None):
        with pytest.raises(ValueError, match="Select an element"):
            await engine.execute_and_record(session.id, RecordedActionType.TAP, element_id="missing")

    engine._executor.execute.assert_not_called()


@pytest.mark.asyncio
async def test_execute_device_action_without_element():
    engine = SmartRecordingEngine(session_manager=InMemoryRecordingSessionManager())
    session = engine._sessions.create("device-1")
    session.state = RecordingState.RECORDING
    engine._sessions.save(session)

    engine._executor = AsyncMock()
    engine._inspection = AsyncMock()
    engine._inspection.refresh_session = AsyncMock(return_value=MagicMock(screenshot_base64=None))

    step = await engine.execute_and_record(session.id, RecordedActionType.PRESS_BACK)
    assert step.action_type == RecordedActionType.PRESS_BACK
    assert step.execution_status == StepExecutionStatus.SUCCESS
    engine._executor.execute.assert_called_once()


@pytest.mark.asyncio
async def test_recording_start_preserves_inspection_session():
    """Starting recording must refresh hierarchy without destroying the live session."""
    engine = SmartRecordingEngine(session_manager=InMemoryRecordingSessionManager())
    mock_inspection = MagicMock()
    existing = MagicMock(device_id="device-1", screenshot_base64="abc", tree={"id": "root"})
    mock_inspection._sessions = {"device-1": existing}
    mock_inspection.refresh_session = AsyncMock(return_value=existing)
    engine._inspection = mock_inspection

    rec = await engine.start("device-1")
    assert rec.state == RecordingState.RECORDING
    assert mock_inspection._sessions["device-1"] is existing
    mock_inspection.refresh_session.assert_called_once()
    assert existing.screenshot_base64 == "abc"
