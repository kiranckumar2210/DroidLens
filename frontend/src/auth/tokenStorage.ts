/** Persist auth tokens — localStorage survives browser refresh; sessionStorage is a same-tab backup. */

const TOKEN_KEY = 'droidlens-auth-token-v1'
const REFRESH_KEY = 'droidlens-auth-refresh-v1'
const SESSION_KEY = 'droidlens-auth-session-v1'
const REMEMBER_KEY = 'droidlens-auth-remember'

function obfuscate(s: string): string {
  try {
    return btoa(encodeURIComponent(s))
  } catch {
    return s
  }
}

function deobfuscate(s: string): string {
  try {
    return decodeURIComponent(atob(s))
  } catch {
    return s
  }
}

function writeToken(key: string, token: string): void {
  const encoded = obfuscate(token)
  localStorage.setItem(key, encoded)
  sessionStorage.setItem(key, encoded)
}

function readToken(key: string): string | null {
  const raw = localStorage.getItem(key) ?? sessionStorage.getItem(key)
  return raw ? deobfuscate(raw) : null
}

function removeToken(key: string): void {
  localStorage.removeItem(key)
  sessionStorage.removeItem(key)
}

export function saveAuthToken(token: string, remember: boolean): void {
  writeToken(TOKEN_KEY, token)
  localStorage.setItem(REMEMBER_KEY, remember ? '1' : '0')
}

export function saveRefreshToken(token: string, remember: boolean): void {
  writeToken(REFRESH_KEY, token)
  localStorage.setItem(REMEMBER_KEY, remember ? '1' : '0')
}

export function loadAuthToken(): string | null {
  return readToken(TOKEN_KEY)
}

export function loadRefreshToken(): string | null {
  return readToken(REFRESH_KEY)
}

export function isRememberMe(): boolean {
  return localStorage.getItem(REMEMBER_KEY) === '1'
}

export function clearAuthToken(): void {
  removeToken(TOKEN_KEY)
  removeToken(REFRESH_KEY)
  localStorage.removeItem(REMEMBER_KEY)
  localStorage.removeItem(SESSION_KEY)
  sessionStorage.removeItem(SESSION_KEY)
}

export function saveCachedSession(json: string): void {
  const encoded = obfuscate(json)
  localStorage.setItem(SESSION_KEY, encoded)
  sessionStorage.setItem(SESSION_KEY, encoded)
}

export function loadCachedSession(): string | null {
  const raw = localStorage.getItem(SESSION_KEY) ?? sessionStorage.getItem(SESSION_KEY)
  return raw ? deobfuscate(raw) : null
}

export function hasStoredCredentials(): boolean {
  return Boolean(loadAuthToken() || loadRefreshToken())
}
