"""Smart Interaction Recorder — inspector-driven command recorder."""

from __future__ import annotations

import time
import uuid
from typing import List, Optional

from inspectiq.domain.models import LocatorCandidate, LocatorScore, LocatorType, Platform
from inspectiq.logging_config import get_logger
from inspectiq.recording.action_execution import AdbActionExecutionService
from inspectiq.recording.code_generation import DefaultCodeGenerationService
from inspectiq.recording.interfaces import RecordingEngine
from inspectiq.recording.locator_resolution import DefaultLocatorResolutionService
from inspectiq.recording.models import (
    CaptureSource,
    RecordedActionType,
    RecordedStep,
    RecordingSession,
    RecordingSettings,
    RecordingState,
    StepExecutionStatus,
    UpdateStepRequest,
    utcnow,
)
from inspectiq.recording.optimizer import RecordingOptimizer
from inspectiq.recording.session_manager import InMemoryRecordingSessionManager
from inspectiq.services.inspection_service import InspectionService

logger = get_logger(__name__)

_DEVICE_ONLY_ACTIONS = frozenset({
    RecordedActionType.PRESS_BACK,
    RecordedActionType.PRESS_HOME,
    RecordedActionType.PRESS_RECENT,
    RecordedActionType.OPEN_NOTIFICATION,
})


class SmartRecordingEngine(RecordingEngine):
    """Inspector-driven recorder: user selects element + action, DroidLens executes and records."""

    def __init__(
        self,
        inspection: Optional[InspectionService] = None,
        session_manager: Optional[InMemoryRecordingSessionManager] = None,
    ):
        self._inspection = inspection or InspectionService()
        self._sessions = session_manager or InMemoryRecordingSessionManager()
        self._locators = DefaultLocatorResolutionService(self._inspection)
        self._codegen = DefaultCodeGenerationService()
        self._optimizer = RecordingOptimizer()
        self._executor = AdbActionExecutionService()

    def _snapshot_undo(self, session: RecordingSession) -> None:
        session.undo_stack.append([s.model_copy(deep=True) for s in session.steps])
        session.redo_stack.clear()
        if len(session.undo_stack) > 50:
            session.undo_stack.pop(0)

    async def start(self, device_id: str, settings: Optional[RecordingSettings] = None) -> RecordingSession:
        session = self._sessions.create(device_id, settings)
        session.state = RecordingState.RECORDING
        session.started_at = utcnow()
        session.steps = []
        session.full_script = self._codegen.script_header(settings or session.settings)
        try:
            live = await self._inspection.refresh_session(device_id, Platform.ANDROID)
            session.initial_screenshot = live.screenshot_base64
        except Exception as exc:
            logger.warning("Could not capture initial snapshot: %s", exc)
        self._sessions.save(session)
        logger.info("Inspector-driven recording started session=%s device=%s", session.id, device_id)
        return session

    def pause(self, session_id: str) -> RecordingSession:
        session = self._require(session_id)
        session.state = RecordingState.PAUSED
        self._sessions.save(session)
        return session

    def resume(self, session_id: str) -> RecordingSession:
        session = self._require(session_id)
        session.state = RecordingState.RECORDING
        self._sessions.save(session)
        return session

    async def stop(self, session_id: str) -> RecordingSession:
        session = self._require(session_id)
        session.state = RecordingState.STOPPED
        session.stopped_at = utcnow()
        if session.started_at:
            session.elapsed_seconds = (session.stopped_at - session.started_at).total_seconds()
        self._optimizer.optimize(session)
        session.full_script = self._codegen.assemble_script(session)
        self._sessions.save(session)
        logger.info("Recording stopped session=%s steps=%d", session_id, len(session.steps))
        return session

    def clear(self, session_id: str) -> RecordingSession:
        session = self._require(session_id)
        self._snapshot_undo(session)
        session.steps = []
        session.full_script = self._codegen.script_header(session.settings)
        self._sessions.save(session)
        return session

    async def execute_and_record(
        self,
        session_id: str,
        action_type: RecordedActionType,
        *,
        element_id: Optional[str] = None,
        x: Optional[int] = None,
        y: Optional[int] = None,
        text_value: Optional[str] = None,
        swipe_direction: Optional[str] = None,
        locator_type: Optional[str] = None,
        locator_value: Optional[str] = None,
    ) -> RecordedStep:
        """Execute action on device, refresh inspector, resolve locator, append to timeline."""
        session = self._require(session_id)
        if session.state != RecordingState.RECORDING:
            raise ValueError("Session is not actively recording")

        self._snapshot_undo(session)
        t0 = time.monotonic()
        status = StepExecutionStatus.SUCCESS
        error_msg: Optional[str] = None
        screenshot_b64: Optional[str] = None

        inspection = self._resolve_inspection(
            session.device_id, element_id=element_id, x=x, y=y, action_type=action_type
        )
        element = inspection.element if inspection else None

        needs_element = action_type not in _DEVICE_ONLY_ACTIONS and action_type not in (
            RecordedActionType.VERIFY_EXISTS,
            RecordedActionType.VERIFY_VISIBLE,
            RecordedActionType.VERIFY_ENABLED,
            RecordedActionType.VERIFY_TEXT,
            RecordedActionType.WAIT,
            RecordedActionType.WAIT_VISIBLE,
            RecordedActionType.WAIT_CLICKABLE,
            RecordedActionType.WAIT_GONE,
        )
        if needs_element and not element:
            raise ValueError("Select an element in the inspector before running this action")

        try:
            await self._executor.execute(
                session.device_id,
                action_type,
                element=element,
                x=x,
                y=y,
                text_value=text_value,
                swipe_direction=swipe_direction,
            )
        except Exception as exc:
            status = StepExecutionStatus.FAILED
            error_msg = str(exc)
            logger.warning("Action execution failed: %s", exc)

        try:
            live = await self._inspection.refresh_session(
                session.device_id, Platform.ANDROID, session.settings.package_name
            )
            if session.settings.capture_screenshots:
                screenshot_b64 = live.screenshot_base64
        except Exception as exc:
            logger.warning("Post-action refresh failed: %s", exc)

        step = self._build_step(
            session,
            action_type,
            inspection=inspection,
            x=x,
            y=y,
            text_value=text_value,
            swipe_direction=swipe_direction,
            locator_type=locator_type,
            locator_value=locator_value,
            execution_status=status,
            execution_time_ms=round((time.monotonic() - t0) * 1000, 1),
            execution_error=error_msg,
            screenshot_base64=screenshot_b64,
        )
        session.steps.append(step)
        try:
            step.code_snippet = step.code_snippet or self._codegen.generate_step_code(step, session.settings)
            self._codegen.append_step(session, step)
        except Exception as exc:
            logger.exception("Live code generation failed for step %s: %s", step.step_number, exc)
            if not step.code_snippet:
                step.code_snippet = (
                    f"# Code generation failed for step {step.step_number}: {exc}\n"
                    f"# Action: {action_type.value} — please fix manually"
                )
            step.needs_review = True
            step.review_reason = step.review_reason or f"Code generation error: {exc}"
            try:
                session.full_script = self._codegen.assemble_script(session)
            except Exception:
                session.full_script = (
                    session.full_script.rstrip()
                    + f"\n\n{step.code_snippet}\n"
                )
        self._sessions.save(session)
        logger.info(
            "Executed+recorded step %d action=%s status=%s confidence=%.2f",
            step.step_number, action_type.value, status.value, step.confidence,
        )
        return step

    def _resolve_inspection(
        self,
        device_id: str,
        *,
        element_id: Optional[str],
        x: Optional[int],
        y: Optional[int],
        action_type: RecordedActionType,
    ):
        if element_id:
            return self._locators.resolve_by_id(device_id, element_id)
        if x is not None and y is not None:
            return self._locators.resolve_at(device_id, x, y, coord_space="screenshot")
        return None

    def _build_step(
        self,
        session: RecordingSession,
        action_type: RecordedActionType,
        *,
        inspection,
        x: Optional[int],
        y: Optional[int],
        text_value: Optional[str],
        swipe_direction: Optional[str],
        locator_type: Optional[str],
        locator_value: Optional[str],
        execution_status: StepExecutionStatus,
        execution_time_ms: float,
        execution_error: Optional[str],
        screenshot_base64: Optional[str],
    ) -> RecordedStep:
        locator = None
        alternatives: List = []
        confidence = 0.0
        needs_review = False
        review_reason = None
        element = None

        if locator_type and locator_value:
            try:
                locator = LocatorCandidate(
                    locator_type=LocatorType(locator_type),
                    value=locator_value,
                    display_name=locator_value,
                    scores=LocatorScore(stability=0.9, uniqueness=0.9, maintainability=0.9, overall=0.9),
                    recommended=True,
                    reason="user override",
                    match_count=1,
                    valid=True,
                )
            except ValueError:
                pass

        if inspection:
            element = inspection.element
            if not locator:
                try:
                    locator = self._locators.pick_best_locator(
                        inspection, session.settings.preferred_locator_strategy
                    )
                    confidence = locator.scores.overall
                    alternatives = self._locators.alternatives(inspection)
                except ValueError:
                    needs_review = True
                    review_reason = "Could not resolve a reliable locator"
                    if inspection.coordinate_fallback:
                        locator = inspection.coordinate_fallback
        elif action_type not in _DEVICE_ONLY_ACTIONS:
            needs_review = True
            review_reason = "No target element resolved"

        if execution_status == StepExecutionStatus.FAILED:
            needs_review = True
            review_reason = execution_error or "Execution failed"

        step = RecordedStep(
            id=uuid.uuid4().hex[:12],
            step_number=len(session.steps) + 1,
            timestamp=utcnow(),
            action_type=action_type,
            source=CaptureSource.INSPECTOR,
            element=element,
            locator=locator,
            alternative_locators=alternatives,
            confidence=confidence,
            coordinates={"x": x, "y": y} if x is not None and y is not None else None,
            text_value=text_value,
            code_snippet="",
            needs_review=needs_review,
            review_reason=review_reason,
            screenshot_base64=screenshot_base64,
            execution_status=execution_status,
            execution_time_ms=execution_time_ms,
            execution_error=execution_error,
        )
        try:
            step.code_snippet = self._codegen.generate_step_code(step, session.settings)
        except Exception as exc:
            logger.exception("Step code snippet generation failed: %s", exc)
            step.code_snippet = f"# Code generation failed: {exc}"
            step.needs_review = True
            step.review_reason = step.review_reason or str(exc)
        return step

    async def record_action(
        self,
        session_id: str,
        action_type: RecordedActionType,
        *,
        x: Optional[int] = None,
        y: Optional[int] = None,
        element_id: Optional[str] = None,
        text_value: Optional[str] = None,
        source: str = "inspector",
        swipe_from: Optional[tuple[int, int]] = None,
        swipe_to: Optional[tuple[int, int]] = None,
    ) -> RecordedStep:
        """Record-only (no device execution) — for manual/imported steps."""
        session = self._require(session_id)
        if session.state not in (RecordingState.RECORDING, RecordingState.PAUSED):
            raise ValueError("Session is not actively recording")

        self._snapshot_undo(session)
        inspection = self._resolve_inspection(
            session.device_id, element_id=element_id, x=x, y=y, action_type=action_type
        )
        step = self._build_step(
            session,
            action_type,
            inspection=inspection,
            x=x,
            y=y,
            text_value=text_value,
            swipe_direction=None,
            locator_type=None,
            locator_value=None,
            execution_status=StepExecutionStatus.SKIPPED,
            execution_time_ms=0,
            execution_error=None,
            screenshot_base64=None,
        )
        session.steps.append(step)
        session.full_script = self._codegen.assemble_script(session)
        self._sessions.save(session)
        return step

    def undo(self, session_id: str) -> RecordingSession:
        session = self._require(session_id)
        if not session.undo_stack:
            return session
        session.redo_stack.append([s.model_copy(deep=True) for s in session.steps])
        session.steps = session.undo_stack.pop()
        session.full_script = self._codegen.assemble_script(session)
        self._sessions.save(session)
        return session

    def redo(self, session_id: str) -> RecordingSession:
        session = self._require(session_id)
        if not session.redo_stack:
            return session
        session.undo_stack.append([s.model_copy(deep=True) for s in session.steps])
        session.steps = session.redo_stack.pop()
        session.full_script = self._codegen.assemble_script(session)
        self._sessions.save(session)
        return session

    def delete_step(self, session_id: str, step_id: str) -> RecordingSession:
        session = self._require(session_id)
        self._snapshot_undo(session)
        session.steps = [s for s in session.steps if s.id != step_id]
        for i, s in enumerate(session.steps, 1):
            s.step_number = i
        session.full_script = self._codegen.assemble_script(session)
        self._sessions.save(session)
        return session

    def reorder_steps(self, session_id: str, step_ids: List[str]) -> RecordingSession:
        session = self._require(session_id)
        self._snapshot_undo(session)
        by_id = {s.id: s for s in session.steps}
        session.steps = [by_id[sid] for sid in step_ids if sid in by_id]
        for i, s in enumerate(session.steps, 1):
            s.step_number = i
        session.full_script = self._codegen.assemble_script(session)
        self._sessions.save(session)
        return session

    def update_step(self, session_id: str, step_id: str, req: UpdateStepRequest) -> RecordingSession:
        session = self._require(session_id)
        self._snapshot_undo(session)
        step = next((s for s in session.steps if s.id == step_id), None)
        if not step:
            raise ValueError(f"Step not found: {step_id}")
        if req.enabled is not None:
            step.enabled = req.enabled
        if req.comment is not None:
            step.comment = req.comment or None
        if req.action_type is not None:
            step.action_type = req.action_type
        if req.text_value is not None:
            step.text_value = req.text_value
        if req.locator_type and req.locator_value and step.locator:
            from inspectiq.domain.models import LocatorType

            try:
                lt = LocatorType(req.locator_type)
            except ValueError:
                lt = step.locator.locator_type
            step.locator = step.locator.model_copy(update={"locator_type": lt, "value": req.locator_value})
            step.code_snippet = self._codegen.generate_step_code(step, session.settings)
        session.full_script = self._codegen.assemble_script(session)
        self._sessions.save(session)
        return session

    def export_json(self, session_id: str) -> dict:
        return self._require(session_id).model_dump(mode="json")

    def export_script(self, session_id: str) -> str:
        session = self._require(session_id)
        self._optimizer.optimize(session)
        return self._codegen.assemble_script(session)

    def export_page_object(self, session_id: str) -> dict:
        from inspectiq.codegen.uiautomator2_generator import UiAutomator2CodeGenerator
        from inspectiq.recording.models import RecordedActionType

        session = self._require(session_id)
        gen = UiAutomator2CodeGenerator()
        page_name = session.settings.page_name or "RecordedScreen"
        class_name = gen._to_class_name(page_name)
        module_name = gen._to_snake(page_name)

        elements: list = []
        seen: set[str] = set()
        for step in session.steps:
            if not step.enabled or not step.element or not step.locator:
                continue
            key = f"{step.locator.locator_type}:{step.locator.value}"
            if key in seen:
                continue
            seen.add(key)
            elements.append((step.element, step.locator))

        page_object = gen.generate_wrapper_export(page_name, elements)

        test_lines = [
            f'"""Auto-generated test for {page_name} — DroidLens Recording Studio."""',
            "",
            "import uiautomator2 as u2",
            "",
            f"# Save page_object.py alongside this file, then: from {module_name} import {class_name}",
            "",
            "",
            f"def test_{module_name}_recorded_flow():",
            "    device = u2.connect()",
            f"    screen = {class_name}(device)",
            "",
        ]
        for step in session.steps:
            if not step.enabled or not step.element or not step.locator:
                continue
            if step.action_type not in (
                RecordedActionType.TAP,
                RecordedActionType.DOUBLE_TAP,
                RecordedActionType.LONG_PRESS,
                RecordedActionType.SET_TEXT,
            ):
                continue
            prop = gen._to_snake(
                step.element.resource_id.split("/")[-1] if step.element.resource_id
                else step.element.text or step.element.content_desc
                or step.element.class_name.split(".")[-1]
            )
            if step.action_type == RecordedActionType.SET_TEXT and step.text_value:
                test_lines.append(f'    screen.{prop}().set_text({step.text_value!r})')
            elif step.action_type == RecordedActionType.LONG_PRESS:
                test_lines.append(f"    screen.{prop}().long_click()")
            elif step.action_type == RecordedActionType.DOUBLE_TAP:
                test_lines.append(f"    screen.{prop}().click()")
                test_lines.append(f"    screen.{prop}().click()")
            else:
                test_lines.append(f"    screen.tap_{prop}()")

        test_lines.extend(["", '    assert device.info.get("currentPackage")', ""])
        test_script = "\n".join(test_lines)

        return {
            "class_name": class_name,
            "page_object": page_object,
            "test_script": test_script,
            "element_count": len(elements),
            "step_count": len([s for s in session.steps if s.enabled]),
        }

    def get_session(self, session_id: str) -> RecordingSession:
        return self._require(session_id)

    def update_settings(self, session_id: str, settings: RecordingSettings) -> RecordingSession:
        session = self._require(session_id)
        session.settings = settings
        try:
            session.full_script = self._codegen.assemble_script(session)
        except Exception as exc:
            logger.exception("Script reassembly failed after settings change: %s", exc)
            for step in session.steps:
                if step.enabled and not step.code_snippet:
                    try:
                        step.code_snippet = self._codegen.generate_step_code(step, settings)
                    except Exception:
                        pass
            session.full_script = self._codegen.assemble_script(session)
        self._sessions.save(session)
        return session

    def _require(self, session_id: str) -> RecordingSession:
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Recording session not found: {session_id}")
        return session
