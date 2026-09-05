"""Recording domain models."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from inspectiq.domain.models import ElementNode, LocatorCandidate


class RecordingState(str, Enum):
    READY = "ready"
    RECORDING = "recording"
    PAUSED = "paused"
    STOPPED = "stopped"
    SAVING = "saving"
    EXPORTED = "exported"


class RecordedActionType(str, Enum):
    TAP = "tap"
    DOUBLE_TAP = "double_tap"
    LONG_PRESS = "long_press"
    SWIPE = "swipe"
    SCROLL = "scroll"
    SET_TEXT = "set_text"
    CLEAR_TEXT = "clear_text"
    PRESS_BACK = "press_back"
    PRESS_HOME = "press_home"
    PRESS_RECENT = "press_recent"
    OPEN_NOTIFICATION = "open_notification"
    WAIT = "wait"
    WAIT_VISIBLE = "wait_visible"
    WAIT_CLICKABLE = "wait_clickable"
    WAIT_GONE = "wait_gone"
    VERIFY_EXISTS = "verify_exists"
    VERIFY_VISIBLE = "verify_visible"
    VERIFY_ENABLED = "verify_enabled"
    VERIFY_TEXT = "verify_text"
    SCREENSHOT = "screenshot"
    LAUNCH_APP = "launch_app"
    CUSTOM = "custom"


class StepExecutionStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class CaptureSource(str, Enum):
    INSPECTOR = "inspector"
    DEVICE = "device"
    MANUAL = "manual"


class RecordingSettings(BaseModel):
    preferred_locator_strategy: str = "auto"
    automatic_waits: bool = True
    wait_timeout: int = 10
    include_comments: bool = True
    capture_screenshots: bool = False
    mask_passwords: bool = True
    variable_naming: str = "snake_case"
    language_profile: str = "python_uiautomator2"
    package_name: str = "com.example.app"
    page_name: str = "RecordedScreen"


class RecordedStep(BaseModel):
    id: str
    step_number: int
    timestamp: datetime
    action_type: RecordedActionType
    source: CaptureSource = CaptureSource.INSPECTOR
    element: Optional[ElementNode] = None
    locator: Optional[LocatorCandidate] = None
    alternative_locators: List[LocatorCandidate] = Field(default_factory=list)
    confidence: float = 0.0
    coordinates: Optional[Dict[str, int]] = None
    text_value: Optional[str] = None
    swipe_from: Optional[Dict[str, int]] = None
    swipe_to: Optional[Dict[str, int]] = None
    code_snippet: str = ""
    enabled: bool = True
    needs_review: bool = False
    review_reason: Optional[str] = None
    comment: Optional[str] = None
    screenshot_base64: Optional[str] = None
    execution_status: StepExecutionStatus = StepExecutionStatus.SUCCESS
    execution_time_ms: float = 0.0
    execution_error: Optional[str] = None


class RecordingSession(BaseModel):
    id: str
    device_id: str
    state: RecordingState = RecordingState.READY
    settings: RecordingSettings = Field(default_factory=RecordingSettings)
    steps: List[RecordedStep] = Field(default_factory=list)
    full_script: str = ""
    started_at: Optional[datetime] = None
    stopped_at: Optional[datetime] = None
    elapsed_seconds: float = 0.0
    undo_stack: List[List[RecordedStep]] = Field(default_factory=list)
    redo_stack: List[List[RecordedStep]] = Field(default_factory=list)
    initial_screenshot: Optional[str] = None


class StartRecordingRequest(BaseModel):
    device_id: str
    settings: Optional[RecordingSettings] = None


class RecordActionRequest(BaseModel):
    action_type: RecordedActionType
    source: CaptureSource = CaptureSource.INSPECTOR
    x: Optional[int] = None
    y: Optional[int] = None
    element_id: Optional[str] = None
    text_value: Optional[str] = None
    swipe_from_x: Optional[int] = None
    swipe_from_y: Optional[int] = None
    swipe_to_x: Optional[int] = None
    swipe_to_y: Optional[int] = None
    swipe_direction: Optional[str] = None
    custom_code: Optional[str] = None
    locator_type: Optional[str] = None
    locator_value: Optional[str] = None


class ExecuteActionRequest(BaseModel):
    """Inspector-driven: execute on device then record."""
    action_type: RecordedActionType
    element_id: Optional[str] = None
    x: Optional[int] = None
    y: Optional[int] = None
    text_value: Optional[str] = None
    swipe_direction: Optional[str] = None
    locator_type: Optional[str] = None
    locator_value: Optional[str] = None


class UpdateStepRequest(BaseModel):
    enabled: Optional[bool] = None
    action_type: Optional[RecordedActionType] = None
    text_value: Optional[str] = None
    locator_type: Optional[str] = None
    locator_value: Optional[str] = None
    comment: Optional[str] = None


class ReorderStepsRequest(BaseModel):
    step_ids: List[str]


class RecordingExportResponse(BaseModel):
    session_id: str
    format: str
    content: str
    step_count: int


class PageObjectExportResponse(BaseModel):
    session_id: str
    class_name: str
    page_object: str
    test_script: str
    element_count: int
    step_count: int


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
