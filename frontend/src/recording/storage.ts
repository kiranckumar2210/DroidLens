import type { RecordingSettings } from './types'
import { DEFAULT_RECORDING_SETTINGS } from './types'
import { DEFAULT_STUDIO_LAYOUT, type StudioLayout } from '../components/ui/TripleSplitPane'

const SETTINGS_KEY = 'droidlens-recording-settings-v1'
const SESSION_KEY = 'droidlens-recording-session-id-v1'

export function loadRecordingSettings(): RecordingSettings {
  try {
    const raw = localStorage.getItem(SETTINGS_KEY)
    if (!raw) return { ...DEFAULT_RECORDING_SETTINGS }
    return { ...DEFAULT_RECORDING_SETTINGS, ...JSON.parse(raw) }
  } catch {
    return { ...DEFAULT_RECORDING_SETTINGS }
  }
}

export function saveRecordingSettings(settings: RecordingSettings): void {
  localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings))
}

export function saveActiveRecordingSessionId(sessionId: string | null): void {
  if (sessionId) {
    sessionStorage.setItem(SESSION_KEY, sessionId)
    localStorage.setItem(SESSION_KEY, sessionId)
  } else {
    sessionStorage.removeItem(SESSION_KEY)
    localStorage.removeItem(SESSION_KEY)
  }
}

export function loadActiveRecordingSessionId(): string | null {
  return sessionStorage.getItem(SESSION_KEY) ?? localStorage.getItem(SESSION_KEY)
}

const STUDIO_LAYOUT_KEY = 'droidlens-recording-studio-layout-v1'

export function loadStudioLayout(): StudioLayout {
  try {
    const raw = localStorage.getItem(STUDIO_LAYOUT_KEY)
    if (!raw) return { ...DEFAULT_STUDIO_LAYOUT }
    const parsed = JSON.parse(raw)
    return {
      ...DEFAULT_STUDIO_LAYOUT,
      ...parsed,
      leftPct: Number(parsed.leftPct) || DEFAULT_STUDIO_LAYOUT.leftPct,
      middlePct: Number(parsed.middlePct) || DEFAULT_STUDIO_LAYOUT.middlePct,
      rightPct: Number(parsed.rightPct) || DEFAULT_STUDIO_LAYOUT.rightPct,
    }
  } catch {
    return { ...DEFAULT_STUDIO_LAYOUT }
  }
}

export function saveStudioLayout(layout: StudioLayout): void {
  localStorage.setItem(STUDIO_LAYOUT_KEY, JSON.stringify(layout))
}
