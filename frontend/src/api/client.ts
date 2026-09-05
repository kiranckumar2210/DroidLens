import type {
  AdbStatus,
  CustomLocatorResult,
  CustomLocatorRule,
  DeviceInfo,
  ElementInspectionResult,
  GeneratedScript,
  InspectionSession,
  LocatorCandidate,
  Platform,
} from '../types'

import { getApiBase, getApiDocsUrl, getWsBase, isElectron, resolveApiBase } from './baseUrl'

export { getApiDocsUrl, getWsBase, isElectron }

let authToken: string | null = null
let refreshHandler: (() => Promise<string | null>) | null = null
let refreshInFlight: Promise<string | null> | null = null

function authHeaders(): Record<string, string> {
  return authToken ? { Authorization: `Bearer ${authToken}` } : {}
}

async function refreshAuthOnce(): Promise<string | null> {
  if (!refreshHandler) return null
  if (refreshInFlight) return refreshInFlight
  refreshInFlight = refreshHandler().finally(() => {
    refreshInFlight = null
  })
  return refreshInFlight
}

async function request<T>(path: string, options?: RequestInit, retry = true): Promise<T> {
  const url = `${resolveApiBase(path)}${path}`
  let res: Response
  try {
    res = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...authHeaders(),
        ...options?.headers,
      },
      ...options,
    })
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err)
    throw new Error(`Network error calling ${url}: ${msg}`)
  }
  if (
    res.status === 401
    && retry
    && refreshHandler
    && path !== '/refresh'
    && !path.includes('/logout')
  ) {
    const newToken = await refreshAuthOnce()
    if (newToken) {
      authToken = newToken
      return request<T>(path, options, false)
    }
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(typeof err.detail === 'string' ? err.detail : JSON.stringify(err.detail))
  }
  return res.json()
}

export const api = {
  setAuthToken: (token: string | null) => { authToken = token },

  setRefreshHandler: (handler: (() => Promise<string | null>) | null) => {
    refreshHandler = handler
  },

  health: () =>
    request<{ status: string; mock_mode: boolean; product: string; adb: AdbStatus }>('/health'),

  adbStatus: () => request<AdbStatus>('/adb/status'),
  adbRestart: () => request<AdbStatus>('/adb/restart', { method: 'POST' }),
  connectWifi: (host: string, port = 5555) =>
    request<{ message: string; devices: DeviceInfo[] }>('/adb/connect-wifi', {
      method: 'POST',
      body: JSON.stringify({ host, port }),
    }),

  listDevices: (refresh = false) =>
    request<{ devices: DeviceInfo[]; mock_mode: boolean }>(
      `/devices?platform=android${refresh ? '&refresh=true' : ''}`
    ),

  listPackages: (deviceId: string, q = '') =>
    request<{ packages: string[] }>(`/devices/${deviceId}/packages?q=${encodeURIComponent(q)}`),

  connect: (device_id: string, platform: Platform = 'android', package_name?: string) =>
    request<InspectionSession>('/session/connect', {
      method: 'POST',
      body: JSON.stringify({ device_id, platform, package: package_name }),
    }),

  refreshSession: (device_id: string, platform: Platform = 'android', package_name?: string) =>
    request<InspectionSession>('/session/refresh', {
      method: 'POST',
      body: JSON.stringify({ device_id, platform, package: package_name }),
    }),

  /** Refresh device UI with retries — uiautomator dump can fail transiently after taps. */
  refreshSessionWithRetry: async (
    device_id: string,
    platform: Platform = 'android',
    package_name?: string,
    attempts = 3,
  ): Promise<InspectionSession> => {
    let lastError: Error | null = null
    for (let i = 0; i < attempts; i++) {
      try {
        return await request<InspectionSession>('/session/refresh', {
          method: 'POST',
          body: JSON.stringify({ device_id, platform, package: package_name }),
        })
      } catch (e) {
        lastError = e as Error
        if (i < attempts - 1) {
          await new Promise((r) => setTimeout(r, 350 * (i + 1)))
        }
      }
    }
    throw lastError ?? new Error('Session refresh failed')
  },

  createOfflineFromContent: (xml_content: string, screenshot_base64?: string) =>
    request<InspectionSession>('/session/offline', {
      method: 'POST',
      body: JSON.stringify({ xml_content, screenshot_base64 }),
    }),

  uploadOffline: async (xmlFile?: File, screenshotFile?: File) => {
    const form = new FormData()
    if (xmlFile) form.append('xml_file', xmlFile)
    if (screenshotFile) form.append('screenshot_file', screenshotFile)
    const res = await fetch(`${resolveApiBase('/session/offline/upload')}/session/offline/upload`, {
      method: 'POST',
      headers: authHeaders(),
      body: form,
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }))
      throw new Error(typeof err.detail === 'string' ? err.detail : JSON.stringify(err.detail))
    }
    return res.json() as Promise<InspectionSession>
  },

  selectAt: (device_id: string, x: number, y: number) =>
    request<ElementInspectionResult>('/inspect/select', {
      method: 'POST',
      body: JSON.stringify({ device_id, x, y }),
    }),

  selectById: (device_id: string, element_id: string) =>
    request<ElementInspectionResult>('/inspect/select-by-id', {
      method: 'POST',
      body: JSON.stringify({ device_id, element_id }),
    }),

  search: (device_id: string, q: string, type = 'all') =>
    request<{ results: ElementInspectionResult['element'][]; count: number }>(
      `/inspect/search?device_id=${device_id}&q=${encodeURIComponent(q)}&type=${type}`
    ),

  launchApp: (device_id: string, package_name: string, activity?: string) =>
    request<{ status: string }>('/app/launch', {
      method: 'POST',
      body: JSON.stringify({ device_id, platform: 'android', package: package_name, activity }),
    }),

  customLocator: (
    device_id: string,
    rules: CustomLocatorRule[],
    options?: {
      axis?: string
      anchor_attribute?: string
      anchor_operator?: string
      anchor_value?: string
      relationship?: string
    },
  ) =>
    request<CustomLocatorResult>(`/locator/custom?device_id=${device_id}`, {
      method: 'POST',
      body: JSON.stringify({ rules, ...options }),
    }),

  saveElement: (payload: Record<string, unknown>) =>
    request<{ element_id: number }>('/storage/save', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  listProjects: () => request<{ projects: unknown[] }>('/storage/projects'),

  getLocatorRepository: () =>
    request<{ elements: Array<Record<string, unknown>> }>('/storage/repository'),

  loadMockSession: () => request<import('../types').InspectionSession>('/session/mock', { method: 'POST' }),

  getSession: (device_id: string) =>
    request<InspectionSession>(`/session/${encodeURIComponent(device_id)}`),

  validateRawLocator: (device_id: string, locator_type: string, expression: string) =>
    request<{
      valid: boolean
      match_count: number
      unique?: boolean
      reliability_score?: number
      warning?: string | null
      error?: string | null
      matched_ids: string[]
    }>('/locator/validate-raw', {
      method: 'POST',
      body: JSON.stringify({ device_id, locator_type, expression }),
    }),

  previewLocator: (device_id: string, locator_type: string, value: string) =>
    request<{
      match_count: number
      valid: boolean
      unique: boolean
      matched_ids: string[]
      execution_ms?: number
      recommendation?: string | null
      warning?: string | null
    }>('/locator/preview', {
      method: 'POST',
      body: JSON.stringify({ device_id, locator_type, value }),
    }),

  getLocatorBundle: (device_id: string, element_id: string) =>
    request<import('../types').LocatorBundle>(`/locator/bundle/${encodeURIComponent(device_id)}/${encodeURIComponent(element_id)}`),

  compareLocators: (device_id: string, locator_a: LocatorCandidate, locator_b: LocatorCandidate) =>
    request<import('../types').LocatorComparisonResult>('/locator/compare', {
      method: 'POST',
      body: JSON.stringify({ device_id, locator_a, locator_b }),
    }),

  generateCode: (
    locator: LocatorCandidate,
    languageProfile = 'python_uiautomator2',
    action = 'click',
    element_name = 'element',
    package_name = 'com.example.app',
  ) =>
    request<GeneratedScript>('/code/generate', {
      method: 'POST',
      body: JSON.stringify({
        locator,
        language: languageProfile.startsWith('java') ? 'java'
          : languageProfile.startsWith('javascript') ? 'javascript'
          : 'python',
        framework: languageProfile.includes('appium') ? 'appium' : 'uiautomator2',
        language_profile: languageProfile,
        action,
        page_name: 'Screen',
        element_name,
        package_name,
      }),
    }),

  register: (full_name: string, email: string, password: string, confirm_password: string) =>
    request<{ session: import('../auth/types').AuthSession }>('/register', {
      method: 'POST',
      body: JSON.stringify({ full_name, email, password, confirm_password }),
    }),

  login: (email: string, password: string, remember_me = false) =>
    request<{ session: import('../auth/types').AuthSession }>('/login', {
      method: 'POST',
      body: JSON.stringify({ email, password, remember_me }),
    }),

  refreshAuth: (refresh_token: string) =>
    request<{ session: import('../auth/types').AuthSession }>('/refresh', {
      method: 'POST',
      body: JSON.stringify({ refresh_token }),
    }),

  logout: (refresh_token?: string | null) =>
    request<{ status: string }>('/logout', {
      method: 'POST',
      body: JSON.stringify({ refresh_token: refresh_token ?? null }),
    }),

  forgotPassword: (email: string) =>
    request<{ status: string; message: string }>('/forgot-password', {
      method: 'POST',
      body: JSON.stringify({ email }),
    }),

  getAccount: () =>
    request<import('../auth/types').AccountSummary>('/profile'),

  updateProfile: (full_name?: string) =>
    request<import('../auth/types').AccountSummary>('/profile', {
      method: 'PATCH',
      body: JSON.stringify({ full_name }),
    }),

  changePassword: (current_password: string, new_password: string, confirm_password: string) =>
    request<{ status: string }>('/auth/change-password', {
      method: 'POST',
      body: JSON.stringify({ current_password, new_password, confirm_password }),
    }),

  deleteAccount: (password: string) =>
    request<{ status: string }>('/auth/delete-account', {
      method: 'POST',
      body: JSON.stringify({ password }),
    }),

  listPlans: () =>
    request<import('../auth/types').PlanPublic[]>('/auth/plans'),

  getPricing: () =>
    request<import('../auth/types').PricingResponse>('/pricing'),

  getSystemConfig: () =>
    request<import('../auth/types').SystemConfig>('/auth/system-config'),

  createPurchase: (plan_id: string) =>
    request<import('../auth/types').PurchaseResult>('/payment/create-order', {
      method: 'POST',
      body: JSON.stringify({ plan_id }),
    }),

  getPurchase: (payment_id: string) =>
    request<import('../auth/types').PurchaseResult>(`/payment/order/${payment_id}`),

  syncPaymentStatus: (payment_id: string) =>
    request<import('../auth/types').OrderStatusResponse>(`/payment/status/${payment_id}`),

  confirmPurchase: (payment_id: string) =>
    request<import('../auth/types').PaymentActionResult>('/payment/verify', {
      method: 'POST',
      body: JSON.stringify({ payment_id }),
    }),

  failPurchase: (payment_id: string) =>
    request<import('../auth/types').PaymentActionResult>('/payment/fail', {
      method: 'POST',
      body: JSON.stringify({ payment_id }),
    }),

  cancelPurchase: (payment_id: string) =>
    request<import('../auth/types').PaymentActionResult>('/payment/cancel', {
      method: 'POST',
      body: JSON.stringify({ payment_id }),
    }),

  startRecording: (device_id: string, settings?: import('../recording/types').RecordingSettings) =>
    request<import('../recording/types').RecordingSession>('/recording/start', {
      method: 'POST',
      body: JSON.stringify({ device_id, settings }),
    }),

  getRecording: (session_id: string) =>
    request<import('../recording/types').RecordingSession>(`/recording/${session_id}`),

  stopRecording: (session_id: string) =>
    request<import('../recording/types').RecordingSession>(`/recording/${session_id}/stop`, { method: 'POST' }),

  pauseRecording: (session_id: string) =>
    request<import('../recording/types').RecordingSession>(`/recording/${session_id}/pause`, { method: 'POST' }),

  resumeRecording: (session_id: string) =>
    request<import('../recording/types').RecordingSession>(`/recording/${session_id}/resume`, { method: 'POST' }),

  clearRecording: (session_id: string) =>
    request<import('../recording/types').RecordingSession>(`/recording/${session_id}/clear`, { method: 'POST' }),

  undoRecording: (session_id: string) =>
    request<import('../recording/types').RecordingSession>(`/recording/${session_id}/undo`, { method: 'POST' }),

  redoRecording: (session_id: string) =>
    request<import('../recording/types').RecordingSession>(`/recording/${session_id}/redo`, { method: 'POST' }),

  recordAction: (session_id: string, body: Record<string, unknown>) =>
    request<import('../recording/types').RecordingSession>(`/recording/${session_id}/action`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  executeRecordingAction: (session_id: string, body: import('../recording/types').ExecuteActionPayload) =>
    request<import('../recording/types').RecordingSession>(`/recording/${session_id}/execute`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  updateRecordingSettings: (session_id: string, settings: import('../recording/types').RecordingSettings) =>
    request<import('../recording/types').RecordingSession>(`/recording/${session_id}/settings`, {
      method: 'PATCH',
      body: JSON.stringify(settings),
    }),

  exportRecordingScript: (session_id: string) =>
    request<{ content: string; step_count: number }>(`/recording/${session_id}/export/script`),

  exportRecordingPageObject: (session_id: string) =>
    request<{
      class_name: string
      page_object: string
      test_script: string
      element_count: number
      step_count: number
    }>(`/recording/${session_id}/export/page-object`),

  xmlDiff: (baseline_xml: string, compare_xml: string) =>
    request<import('../components/XmlDiffDialog').XmlDiffResult>('/offline/xml-diff', {
      method: 'POST',
      body: JSON.stringify({ baseline_xml, compare_xml }),
    }),

  locatorHealthScan: (xml_content: string, screen_name = 'Screen') =>
    request<import('../components/LocatorHealthDialog').LocatorHealthReport>('/offline/locator-health', {
      method: 'POST',
      body: JSON.stringify({ xml_content, screen_name }),
    }),

  validateLocatorsOffline: (
    xml_content: string,
    locators: unknown,
    screen_name = 'Screen',
    require_unique = true,
  ) =>
    request<{
      passed: number
      failed: number
      total: number
      ok: boolean
      results: Array<{
        screen: string
        element_name: string
        locator_type: string
        value: string
        valid: boolean
        match_count: number
        error?: string
        warning?: string
      }>
    }>('/offline/validate-locators', {
      method: 'POST',
      body: JSON.stringify({ xml_content, locators, screen_name, require_unique }),
    }),

  locatorMigrate: (old_xml: string, new_xml: string, locator_type: string, locator_value: string) =>
    request<{
      status: string
      message: string
      old_match_count: number
      new_match_count: number
      suggestions: Array<{
        reason: string
        element_id: string
        resource_id?: string
        class_name: string
        locators: Array<{
          locator_type: string
          value: string
          display_name: string
          recommended: boolean
          overall_score: number
        }>
      }>
    }>('/offline/locator-migrate', {
      method: 'POST',
      body: JSON.stringify({ old_xml, new_xml, locator_type, locator_value }),
    }),

  deleteRecordingStep: (session_id: string, step_id: string) =>
    request<import('../recording/types').RecordingSession>(`/recording/${session_id}/steps/${step_id}`, {
      method: 'DELETE',
    }),

  reorderRecordingSteps: (session_id: string, step_ids: string[]) =>
    request<import('../recording/types').RecordingSession>(`/recording/${session_id}/reorder`, {
      method: 'POST',
      body: JSON.stringify({ step_ids }),
    }),

  updateRecordingStep: (
    session_id: string,
    step_id: string,
    patch: { enabled?: boolean; comment?: string },
  ) =>
    request<import('../recording/types').RecordingSession>(`/recording/${session_id}/steps/${step_id}`, {
      method: 'PATCH',
      body: JSON.stringify(patch),
    }),
}
