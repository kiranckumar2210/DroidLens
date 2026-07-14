"""In-memory recording session store with optional JSON persistence."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Dict, Optional

from inspectiq.recording.interfaces import RecordingSessionManager
from inspectiq.recording.models import RecordingSession, RecordingSettings


class InMemoryRecordingSessionManager(RecordingSessionManager):
    def __init__(self, persist_dir: Optional[str] = None):
        self._sessions: Dict[str, RecordingSession] = {}
        self._device_index: Dict[str, str] = {}
        home = Path.home() / ".droidlens" / "recordings"
        self._persist_dir = Path(persist_dir) if persist_dir else home
        self._persist_dir.mkdir(parents=True, exist_ok=True)

    def create(self, device_id: str, settings: Optional[RecordingSettings] = None) -> RecordingSession:
        existing = self.get_active_for_device(device_id)
        if existing and existing.state.value in ("recording", "paused"):
            return existing
        sid = uuid.uuid4().hex
        session = RecordingSession(
            id=sid,
            device_id=device_id,
            settings=settings or RecordingSettings(),
        )
        self._sessions[sid] = session
        self._device_index[device_id] = sid
        return session

    def get(self, session_id: str) -> Optional[RecordingSession]:
        session = self._sessions.get(session_id)
        if session:
            return session
        return self.load(session_id)

    def get_active_for_device(self, device_id: str) -> Optional[RecordingSession]:
        sid = self._device_index.get(device_id)
        return self._sessions.get(sid) if sid else None

    def save(self, session: RecordingSession) -> None:
        self._sessions[session.id] = session
        self._device_index[session.device_id] = session.id
        path = self._persist_dir / f"{session.id}.json"
        path.write_text(session.model_dump_json(indent=2), encoding="utf-8")

    def load(self, session_id: str) -> Optional[RecordingSession]:
        path = self._persist_dir / f"{session_id}.json"
        if not path.exists():
            return None
        session = RecordingSession.model_validate_json(path.read_text(encoding="utf-8"))
        self._sessions[session.id] = session
        self._device_index[session.device_id] = session.id
        return session

    def delete(self, session_id: str) -> None:
        session = self._sessions.pop(session_id, None)
        if session:
            self._device_index.pop(session.device_id, None)
            path = self._persist_dir / f"{session_id}.json"
            if path.exists():
                path.unlink()

    def list_saved(self) -> list[str]:
        return [p.stem for p in self._persist_dir.glob("*.json")]
