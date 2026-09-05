/** API base URL — `/api` in Vite dev (proxied), same-origin or VITE_API_BASE in production. */
export function getApiBase(): string {
  const explicit = window.droidlens?.apiBase ?? window.inspectiq?.apiBase
  if (explicit !== undefined) return explicit
  const fromEnv = import.meta.env.VITE_API_BASE as string | undefined
  if (fromEnv) return fromEnv.replace(/\/$/, '')
  if (import.meta.env.DEV) return '/api'
  return ''
}

/** Cloud auth API — login, billing, admin (desktop hybrid mode). Falls back to local API base. */
export function getAuthApiBase(): string {
  const cloud = window.droidlens?.authApiBase ?? window.inspectiq?.authApiBase
  if (cloud) return cloud.replace(/\/$/, '')
  const fromEnv = import.meta.env.VITE_AUTH_API_BASE as string | undefined
  if (fromEnv) return fromEnv.replace(/\/$/, '')
  return getApiBase()
}

/** WebSocket base — local backend in Electron; same host or VITE_WS_BASE in production. */
export function getWsBase(): string {
  const explicit = window.droidlens?.wsBase ?? window.inspectiq?.wsBase
  if (explicit) return explicit.replace(/\/$/, '')
  const fromEnv = import.meta.env.VITE_WS_BASE as string | undefined
  if (fromEnv) return fromEnv.replace(/\/$/, '')
  if (import.meta.env.DEV) return 'ws://127.0.0.1:8765'
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${proto}//${window.location.host}`
}

export function getApiDocsUrl(): string {
  const base = window.droidlens?.apiBase ?? window.inspectiq?.apiBase
  if (base?.startsWith('http')) return `${base.replace(/\/$/, '')}/docs`
  const fromEnv = import.meta.env.VITE_API_BASE as string | undefined
  if (fromEnv) return `${fromEnv.replace(/\/$/, '')}/docs`
  if (import.meta.env.DEV) return 'http://127.0.0.1:8765/docs'
  return `${window.location.origin}/docs`
}

export const isElectron = (): boolean =>
  Boolean(window.droidlens?.isElectron || window.inspectiq?.isElectron)

export function usesCloudAuth(): boolean {
  return getAuthApiBase() !== getApiBase()
}

function isAuthApiPath(path: string): boolean {
  const normalized = path.split('?')[0]
  if (normalized.startsWith('/admin')) return true
  if (normalized.startsWith('/auth/')) return true
  if (normalized.startsWith('/payment/')) return true
  return [
    '/register',
    '/login',
    '/refresh',
    '/logout',
    '/forgot-password',
    '/profile',
    '/pricing',
  ].includes(normalized)
}

export function resolveApiBase(path: string): string {
  return isAuthApiPath(path) ? getAuthApiBase() : getApiBase()
}
