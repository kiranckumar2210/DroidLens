"""Live code generation during recording."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from inspectiq.domain.models import ElementNode, LocatorCandidate, LocatorScore, LocatorType
from inspectiq.recording.code_generation import DefaultCodeGenerationService
from inspectiq.recording.engine import SmartRecordingEngine
from inspectiq.recording.models import RecordedActionType, RecordingSettings, RecordingState
from inspectiq.recording.session_manager import InMemoryRecordingSessionManager


@pytest.mark.asyncio
async def test_start_initializes_live_script_header():
    engine = SmartRecordingEngine(session_manager=InMemoryRecordingSessionManager())
    engine._inspection = AsyncMock()
    engine._inspection.refresh_session = AsyncMock(return_value=MagicMock(screenshot_base64=None))
    session = await engine.start("device-1", RecordingSettings(language_profile="python_uiautomator2"))
    assert "uiautomator2" in session.full_script
    assert session.steps == []


def test_append_step_updates_full_script_incrementally():
    gen = DefaultCodeGenerationService()
    from inspectiq.recording.models import RecordingSession, RecordedStep, utcnow
    import uuid

    settings = RecordingSettings(language_profile="python_uiautomator2")
    session = RecordingSession(id="s1", device_id="d1", settings=settings)
    session.full_script = gen.script_header(settings)

    step = RecordedStep(
        id=uuid.uuid4().hex[:8],
        step_number=1,
        timestamp=utcnow(),
        action_type=RecordedActionType.PRESS_BACK,
        code_snippet="d.press('back')",
    )
    gen.append_step(session, step)
    assert "d.press('back')" in session.full_script
    assert "uiautomator2" in session.full_script


@pytest.mark.asyncio
async def test_execute_and_record_returns_live_full_script():
    engine = SmartRecordingEngine(session_manager=InMemoryRecordingSessionManager())
    session = engine._sessions.create("device-1")
    session.state = RecordingState.RECORDING
    session.settings = RecordingSettings(language_profile="python_uiautomator2")
    session.full_script = engine._codegen.script_header(session.settings)
    engine._sessions.save(session)

    mock_inspection = MagicMock()
    mock_inspection.element = ElementNode(
        id="el1",
        class_name="android.widget.Button",
        resource_id="com.demo:id/login",
        clickable=True,
    )
    mock_inspection.coordinate_fallback = None
    loc = LocatorCandidate(
        locator_type=LocatorType.RESOURCE_ID,
        value="com.demo:id/login",
        display_name="Resource ID",
        scores=LocatorScore(stability=0.9, uniqueness=0.9, maintainability=0.9, overall=0.9),
        recommended=True,
        reason="test",
    )
    engine._locators.resolve_by_id = MagicMock(return_value=mock_inspection)
    engine._locators.pick_best_locator = MagicMock(return_value=loc)
    engine._locators.alternatives = MagicMock(return_value=[])
    engine._executor = AsyncMock()
    engine._inspection = AsyncMock()
    engine._inspection.refresh_session = AsyncMock(return_value=MagicMock(screenshot_base64=None))

    await engine.execute_and_record(session.id, RecordedActionType.TAP, element_id="el1")
    updated = engine.get_session(session.id)
    assert len(updated.steps) == 1
    assert updated.full_script.strip()
    assert updated.steps[0].code_snippet
    assert "login" in updated.full_script.lower() or "click" in updated.full_script.lower()


def test_append_step_python_appium_with_automatic_waits():
    """Regression: LocatorType.DESCRIPTION typo broke live recording for Appium Python."""
    gen = DefaultCodeGenerationService()
    from inspectiq.recording.models import RecordingSession, RecordedStep, utcnow
    import uuid

    settings = RecordingSettings(language_profile="python_appium", automatic_waits=True)
    session = RecordingSession(id="s1", device_id="d1", settings=settings)
    session.full_script = gen.script_header(settings)

    el = ElementNode(
        id="el1",
        platform="android",
        class_name="android.widget.Button",
        resource_id="com.demo:id/login",
        clickable=True,
        enabled=True,
        visible=True,
        scrollable=False,
        focusable=True,
        focused=False,
        checkable=False,
        checked=False,
        selected=False,
        password=False,
        long_clickable=False,
        index=0,
    )
    loc = LocatorCandidate(
        locator_type=LocatorType.RESOURCE_ID,
        value="com.demo:id/login",
        display_name="Resource ID",
        scores=LocatorScore(stability=0.9, uniqueness=0.9, maintainability=0.9, overall=0.9),
        recommended=True,
        reason="test",
    )
    step = RecordedStep(
        id=uuid.uuid4().hex[:8],
        step_number=1,
        timestamp=utcnow(),
        action_type=RecordedActionType.TAP,
        element=el,
        locator=loc,
        confidence=0.9,
    )
    step.code_snippet = gen.generate_step_code(step, settings)
    assert "driver.find_element" in step.code_snippet
    assert "driver.quit()" not in step.code_snippet
    gen.append_step(session, step)
    assert "wait.until" in session.full_script
    assert "login" in session.full_script.lower()
