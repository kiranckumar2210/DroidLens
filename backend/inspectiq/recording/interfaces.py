"""Recording engine interfaces — extensible for iOS, Flutter, AI healing."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from inspectiq.domain.models import ElementInspectionResult, ElementNode, LocatorCandidate
from inspectiq.recording.models import (
    RecordedActionType,
    RecordedStep,
    RecordingSession,
    RecordingSettings,
)


class ActionExecutionService(ABC):
    """Executes inspector-selected actions on the connected device."""

    @abstractmethod
    async def execute(
        self,
        device_id: str,
        action_type: RecordedActionType,
        *,
        element: Optional[ElementNode] = None,
        x: Optional[int] = None,
        y: Optional[int] = None,
        text_value: Optional[str] = None,
        swipe_direction: Optional[str] = None,
    ) -> None:
        ...


class LocatorResolutionService(ABC):
    @abstractmethod
    def resolve_at(self, device_id: str, x: int, y: int) -> Optional[ElementInspectionResult]:
        ...

    @abstractmethod
    def resolve_by_id(self, device_id: str, element_id: str) -> Optional[ElementInspectionResult]:
        ...

    @abstractmethod
    def pick_best_locator(self, inspection: ElementInspectionResult, strategy: str = "auto") -> LocatorCandidate:
        ...


class CodeGenerationService(ABC):
    @abstractmethod
    def generate_step_code(
        self,
        step: RecordedStep,
        settings: RecordingSettings,
    ) -> str:
        ...

    @abstractmethod
    def assemble_script(self, session: RecordingSession) -> str:
        ...


class EventCaptureService(ABC):
    @abstractmethod
    async def start_device_monitor(self, device_id: str, callback) -> None:
        ...

    @abstractmethod
    async def stop_device_monitor(self, device_id: str) -> None:
        ...


class RecordingSessionManager(ABC):
    @abstractmethod
    def create(self, device_id: str, settings: Optional[RecordingSettings] = None) -> RecordingSession:
        ...

    @abstractmethod
    def get(self, session_id: str) -> Optional[RecordingSession]:
        ...

    @abstractmethod
    def get_active_for_device(self, device_id: str) -> Optional[RecordingSession]:
        ...

    @abstractmethod
    def save(self, session: RecordingSession) -> None:
        ...

    @abstractmethod
    def delete(self, session_id: str) -> None:
        ...


class RecordingEngine(ABC):
    @abstractmethod
    async def start(self, device_id: str, settings: Optional[RecordingSettings] = None) -> RecordingSession:
        ...

    @abstractmethod
    def pause(self, session_id: str) -> RecordingSession:
        ...

    @abstractmethod
    def resume(self, session_id: str) -> RecordingSession:
        ...

    @abstractmethod
    async def stop(self, session_id: str) -> RecordingSession:
        ...

    @abstractmethod
    def clear(self, session_id: str) -> RecordingSession:
        ...

    @abstractmethod
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
        ...

    @abstractmethod
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
        ...

    @abstractmethod
    def undo(self, session_id: str) -> RecordingSession:
        ...

    @abstractmethod
    def redo(self, session_id: str) -> RecordingSession:
        ...

    @abstractmethod
    def delete_step(self, session_id: str, step_id: str) -> RecordingSession:
        ...

    @abstractmethod
    def reorder_steps(self, session_id: str, step_ids: List[str]) -> RecordingSession:
        ...

    @abstractmethod
    def export_json(self, session_id: str) -> dict:
        ...

    @abstractmethod
    def export_script(self, session_id: str) -> str:
        ...
