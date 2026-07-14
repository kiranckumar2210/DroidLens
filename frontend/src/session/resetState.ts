import { saveActiveRecordingSessionId } from '../recording/storage'
import { clearPersistedInspectorState, defaultPersistedState, savePersistedState } from './storage'

/** Clear all persisted UI/session state after a crash or stuck recorder. */
export function resetApplicationState(): void {
  clearPersistedInspectorState()
  savePersistedState(defaultPersistedState())
  saveActiveRecordingSessionId(null)
  try {
    sessionStorage.removeItem('droidlens-recording-settings-v1')
  } catch { /* ignore */ }
}
