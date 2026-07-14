/** Smart Interaction Recorder — shared types */

export type RecordingState = 'ready' | 'recording' | 'paused' | 'stopped' | 'saving' | 'exported'

export type RecordedActionType =
  | 'tap'
  | 'double_tap'
  | 'long_press'
  | 'swipe'
  | 'scroll'
  | 'set_text'
  | 'clear_text'
  | 'press_back'
  | 'press_home'
  | 'press_recent'
  | 'open_notification'
  | 'wait'
  | 'wait_visible'
  | 'wait_clickable'
  | 'wait_gone'
  | 'verify_exists'
  | 'verify_visible'
  | 'verify_enabled'
  | 'verify_text'
  | 'screenshot'
  | 'launch_app'
  | 'custom'

export type StepExecutionStatus = 'success' | 'failed' | 'skipped'

export type CaptureSource = 'inspector' | 'device' | 'manual'

export interface RecordingSettings {
  preferred_locator_strategy: string
  automatic_waits: boolean
  wait_timeout: number
  include_comments: boolean
  capture_screenshots: boolean
  mask_passwords: boolean
  variable_naming: string
  language_profile: string
  package_name: string
  page_name: string
}

export interface RecordedStep {
  id: string
  step_number: number
  timestamp: string
  action_type: RecordedActionType
  source: CaptureSource
  element?: Record<string, unknown> | null
  locator?: Record<string, unknown> | null
  alternative_locators?: Record<string, unknown>[]
  confidence: number
  coordinates?: { x: number; y: number } | null
  text_value?: string | null
  code_snippet: string
  enabled: boolean
  needs_review: boolean
  review_reason?: string | null
  comment?: string | null
  execution_status?: StepExecutionStatus
  execution_time_ms?: number
  execution_error?: string | null
}

export interface ExecuteActionPayload {
  action_type: RecordedActionType
  element_id?: string
  text_value?: string
  swipe_direction?: string
  locator_type?: string
  locator_value?: string
}

export interface RecordingSession {
  id: string
  device_id: string
  state: RecordingState
  settings: RecordingSettings
  steps: RecordedStep[]
  full_script: string
  started_at?: string | null
  stopped_at?: string | null
  elapsed_seconds: number
}

export const DEFAULT_RECORDING_SETTINGS: RecordingSettings = {
  preferred_locator_strategy: 'auto',
  automatic_waits: true,
  wait_timeout: 10,
  include_comments: true,
  capture_screenshots: false,
  mask_passwords: true,
  variable_naming: 'snake_case',
  language_profile: 'python_uiautomator2',
  package_name: 'com.example.app',
  page_name: 'RecordedScreen',
}

export const LANGUAGE_PROFILES = [
  { id: 'python_uiautomator2', label: 'Python — UIAutomator2' },
  { id: 'python_appium', label: 'Python — Appium' },
  { id: 'java_uiautomator', label: 'Java — UIAutomator' },
  { id: 'java_appium', label: 'Java — Appium' },
  { id: 'javascript_wdio', label: 'JavaScript — WebdriverIO' },
  { id: 'javascript_appium', label: 'JavaScript — Appium' },
  { id: 'adb_shell', label: 'ADB Shell' },
]
