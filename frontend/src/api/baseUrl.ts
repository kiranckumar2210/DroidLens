/** API base URL — `/api` in Vite dev (proxied), same-origin or VITE_API_BASE in production. */
export function getApiBase(): string {
  const explicit = window.droidlens?.apiBase ?? window.inspectiq?.apiBase
  if (explicit !== undefined) return explicit
  const fromEnv = import.meta.env.VITE_API_BASE as string | undefined
  if (fromEnv) return fromEnv.replace(/\/$/, '')
  if (import.meta.env.DEV) return '/api'
  return ''
}

/** WebSocket base — same host in production, VITE_WS_BASE, or local backend in Electron dev. */
export function getWsBase(): string {
  const explicit = window.droidlens?.wsBase ?? window.inspectiq?.wsBase
  if (explicit) return explicit.replace(/\/$/, '')
  const fromEnv = import.meta.env.VITE_WS_BASE as string | undefined
  if (fromEnv) return fromEnv.replace(/\/$/, '')
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
