"""Smart Interaction Recorder REST API."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from inspectiq.auth.dependencies import require_premium
from inspectiq.recording.engine import SmartRecordingEngine
from inspectiq.recording.models import (
    RecordActionRequest,
    ExecuteActionRequest,
    RecordingExportResponse,
    RecordingSession,
    RecordingSettings,
    ReorderStepsRequest,
    StartRecordingRequest,
    UpdateStepRequest,
)
from inspectiq.services.inspection_service import InspectionService

router = APIRouter(prefix="/recording", tags=["recording"])

_engine: SmartRecordingEngine | None = None


def configure_recording_engine(inspection: InspectionService) -> SmartRecordingEngine:
    """Bind recorder to the app's shared inspection service (single hierarchy cache)."""
    global _engine
    _engine = SmartRecordingEngine(inspection)
    return _engine


def get_engine() -> SmartRecordingEngine:
    if _engine is None:
        raise RuntimeError("Recording engine not configured — call configure_recording_engine() at startup")
    return _engine


@router.post("/start", response_model=RecordingSession)
async def start_recording(
    req: StartRecordingRequest,
    _user=Depends(require_premium),
    engine: SmartRecordingEngine = Depends(get_engine),
):
    try:
        return await engine.start(req.device_id, req.settings)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{session_id}/pause", response_model=RecordingSession)
def pause_recording(session_id: str, _user=Depends(require_premium), engine: SmartRecordingEngine = Depends(get_engine)):
    try:
        return engine.pause(session_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{session_id}/resume", response_model=RecordingSession)
def resume_recording(session_id: str, _user=Depends(require_premium), engine: SmartRecordingEngine = Depends(get_engine)):
    try:
        return engine.resume(session_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{session_id}/stop", response_model=RecordingSession)
async def stop_recording(session_id: str, _user=Depends(require_premium), engine: SmartRecordingEngine = Depends(get_engine)):
    try:
        return await engine.stop(session_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{session_id}/clear", response_model=RecordingSession)
def clear_recording(session_id: str, _user=Depends(require_premium), engine: SmartRecordingEngine = Depends(get_engine)):
    try:
        return engine.clear(session_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{session_id}", response_model=RecordingSession)
def get_recording(session_id: str, _user=Depends(require_premium), engine: SmartRecordingEngine = Depends(get_engine)):
    try:
        return engine.get_session(session_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{session_id}/execute", response_model=RecordingSession)
async def execute_and_record(
    session_id: str,
    req: ExecuteActionRequest,
    _user=Depends(require_premium),
    engine: SmartRecordingEngine = Depends(get_engine),
):
    """Inspector-driven: execute action on device, refresh UI, record step + codegen."""
    try:
        await engine.execute_and_record(
            session_id,
            req.action_type,
            element_id=req.element_id,
            x=req.x,
            y=req.y,
            text_value=req.text_value,
            swipe_direction=req.swipe_direction,
            locator_type=req.locator_type,
            locator_value=req.locator_value,
        )
        return engine.get_session(session_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{session_id}/action", response_model=RecordingSession)
async def record_action(
    session_id: str,
    req: RecordActionRequest,
    _user=Depends(require_premium),
    engine: SmartRecordingEngine = Depends(get_engine),
):
    try:
        swipe_from = None
        swipe_to = None
        if req.swipe_from_x is not None and req.swipe_from_y is not None:
            swipe_from = (req.swipe_from_x, req.swipe_from_y)
        if req.swipe_to_x is not None and req.swipe_to_y is not None:
            swipe_to = (req.swipe_to_x, req.swipe_to_y)
        await engine.record_action(
            session_id,
            req.action_type,
            x=req.x,
            y=req.y,
            element_id=req.element_id,
            text_value=req.text_value,
            source=req.source.value,
            swipe_from=swipe_from,
            swipe_to=swipe_to,
        )
        return engine.get_session(session_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{session_id}/undo", response_model=RecordingSession)
def undo(session_id: str, _user=Depends(require_premium), engine: SmartRecordingEngine = Depends(get_engine)):
    return engine.undo(session_id)


@router.post("/{session_id}/redo", response_model=RecordingSession)
def redo(session_id: str, _user=Depends(require_premium), engine: SmartRecordingEngine = Depends(get_engine)):
    return engine.redo(session_id)


@router.delete("/{session_id}/steps/{step_id}", response_model=RecordingSession)
def delete_step(session_id: str, step_id: str, _user=Depends(require_premium), engine: SmartRecordingEngine = Depends(get_engine)):
    return engine.delete_step(session_id, step_id)


@router.patch("/{session_id}/steps/{step_id}", response_model=RecordingSession)
def update_step(
    session_id: str,
    step_id: str,
    req: UpdateStepRequest,
    _user=Depends(require_premium),
    engine: SmartRecordingEngine = Depends(get_engine),
):
    try:
        return engine.update_step(session_id, step_id, req)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{session_id}/reorder", response_model=RecordingSession)
def reorder_steps(
    session_id: str,
    req: ReorderStepsRequest,
    _user=Depends(require_premium),
    engine: SmartRecordingEngine = Depends(get_engine),
):
    return engine.reorder_steps(session_id, req.step_ids)


@router.patch("/{session_id}/settings", response_model=RecordingSession)
def update_settings(
    session_id: str,
    settings: RecordingSettings,
    _user=Depends(require_premium),
    engine: SmartRecordingEngine = Depends(get_engine),
):
    return engine.update_settings(session_id, settings)


@router.get("/{session_id}/export/script", response_model=RecordingExportResponse)
def export_script(session_id: str, _user=Depends(require_premium), engine: SmartRecordingEngine = Depends(get_engine)):
    try:
        content = engine.export_script(session_id)
        session = engine.get_session(session_id)
        return RecordingExportResponse(
            session_id=session_id,
            format="script",
            content=content,
            step_count=len(session.steps),
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{session_id}/export/json")
def export_json(session_id: str, _user=Depends(require_premium), engine: SmartRecordingEngine = Depends(get_engine)):
    try:
        return engine.export_json(session_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
