import type { InspectionSession, Platform } from '../types'
import type { InspectorSection } from '../components/InspectorPanel'
import { DEFAULT_BUILDER, type BuilderState } from '../components/InspectorPanel'

export type AppScreen = 'dashboard' | 'inspector'
export type SessionKind = 'live' | 'offline' | 'mock'

const STORAGE_KEY = 'droidlens-inspection-session-v1'

export interface PersistedInspectionState {
  screen: AppScreen
  sessionKind: SessionKind
  deviceId: string
  platform: Platform
  liveRefresh: boolean
  packageName: string
  activity: string
  languageProfile: string
  codeAction: string
  inspectorSection: InspectorSection
  builderState: BuilderState
  selectedElementId: string | null
  /** Lightweight session fingerprint for restore — full tree loaded from API */
  sessionDeviceId: string | null
  sessionMode: string | null
  recordingModeOpen: boolean
}

export function defaultPersistedState(): PersistedInspectionState {
  return {
    screen: 'dashboard',
    sessionKind: 'mock',
    deviceId: '',
    platform: 'android',
    liveRefresh: false,
    packageName: '',
    activity: '',
    languageProfile: 'python_uiautomator2',
    codeAction: 'click',
    inspectorSection: 'locators',
    builderState: DEFAULT_BUILDER,
    selectedElementId: null,
    sessionDeviceId: null,
    sessionMode: null,
    recordingModeOpen: false,
  }
}

export function loadPersistedState(): PersistedInspectionState {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY) ?? localStorage.getItem(STORAGE_KEY)
    if (!raw) return defaultPersistedState()
    return { ...defaultPersistedState(), ...JSON.parse(raw) }
  } catch {
    return defaultPersistedState()
  }
}

export function savePersistedState(state: PersistedInspectionState): void {
  try {
    const json = JSON.stringify(state)
    sessionStorage.setItem(STORAGE_KEY, json)
    localStorage.setItem(STORAGE_KEY, json)
  } catch {
    /* quota or private mode — ignore */
  }
}

export function clearPersistedInspectorState(): void {
  sessionStorage.removeItem(STORAGE_KEY)
  localStorage.removeItem(STORAGE_KEY)
}

export function snapshotFromSession(session: InspectionSession | null): Pick<
  PersistedInspectionState,
  'sessionDeviceId' | 'sessionMode'
> {
  if (!session) return { sessionDeviceId: null, sessionMode: null }
  return {
    sessionDeviceId: session.device_id,
    sessionMode: session.mode,
  }
}
