import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import { api } from '../api/client'
import { withTimeout } from '../utils/withTimeout'
import { FeatureAccessManager, resolveUserTier, type AccessResult } from './features'
import { useSystemConfig } from './SystemConfigContext'
import {
  clearAuthToken,
  hasStoredCredentials,
  isRememberMe,
  loadAuthToken,
  loadCachedSession,
  loadRefreshToken,
  saveAuthToken,
  saveCachedSession,
  saveRefreshToken,
} from './tokenStorage'
import type {
  AppFeature,
  AuthSession,
  AuthUser,
  LicenseInfo,
  PremiumFeature,
  UserTier,
  AccountSummary,
} from './types'

interface AuthContextValue {
  user: AuthUser | null
  license: LicenseInfo | null
  isLoggedIn: boolean
  isAdmin: boolean
  tier: UserTier
  loading: boolean
  login: (email: string, password: string, rememberMe: boolean) => Promise<void>
  register: (fullName: string, email: string, password: string, confirm: string) => Promise<void>
  logout: () => void
  refreshAccount: () => Promise<boolean>
  canAccess: (feature: AppFeature) => AccessResult
}

const guestLicense: LicenseInfo = {
  status: 'guest',
  plan_id: 'guest',
  plan_name: 'Guest',
  has_premium: false,
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}

function parseCachedSession(): { user: AuthUser; license: LicenseInfo } | null {
  const cached = loadCachedSession()
  if (!cached) return null
  try {
    const parsed = JSON.parse(cached)
    if (parsed?.user && parsed?.license) return parsed
  } catch { /* ignore */ }
  return null
}

function isAuthError(message: string): boolean {
  const lower = message.toLowerCase()
  return lower.includes('401')
    || lower.includes('invalid')
    || lower.includes('revoked')
    || lower.includes('expired')
    || lower.includes('authentication required')
}

function persistSession(session: AuthSession, remember: boolean) {
  saveAuthToken(session.access_token, remember)
  saveRefreshToken(session.refresh_token, remember)
  api.setAuthToken(session.access_token)
  saveCachedSession(JSON.stringify({ user: session.user, license: session.license }))
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const { config } = useSystemConfig()
  const cached = parseCachedSession()
  const [user, setUser] = useState<AuthUser | null>(cached?.user ?? null)
  const [license, setLicense] = useState<LicenseInfo | null>(cached?.license ?? null)
  const [loading, setLoading] = useState(true)

  const applySession = useCallback((session: AuthSession, remember = isRememberMe()) => {
    setUser(session.user)
    setLicense(session.license)
    persistSession(session, remember)
  }, [])

  const clearSession = useCallback(() => {
    setUser(null)
    setLicense(null)
    clearAuthToken()
    api.setAuthToken(null)
  }, [])

  const logout = useCallback(() => {
    const refresh = loadRefreshToken()
    if (loadAuthToken()) {
      api.logout(refresh).catch(() => {})
    }
    clearSession()
  }, [clearSession])

  const refreshAccount = useCallback(async (): Promise<boolean> => {
    const token = loadAuthToken()
    if (!token) return false
    api.setAuthToken(token)
    try {
      const account: AccountSummary = await api.getAccount()
      setUser(account.user)
      setLicense(account.license)
      saveCachedSession(JSON.stringify({ user: account.user, license: account.license }))
      return true
    } catch {
      return false
    }
  }, [])

  const tryRefreshToken = useCallback(async (): Promise<string | null> => {
    const refresh = loadRefreshToken()
    if (!refresh) return null
    try {
      const result = await api.refreshAuth(refresh)
      applySession(result.session, isRememberMe())
      return result.session.access_token
    } catch (e) {
      clearSession()
      return null
    }
  }, [applySession])

  useEffect(() => {
    api.setRefreshHandler(tryRefreshToken)
    return () => api.setRefreshHandler(null)
  }, [tryRefreshToken])

  useEffect(() => {
    const init = async () => {
      const token = loadAuthToken()
      const refresh = loadRefreshToken()

      if (token) api.setAuthToken(token)

      try {
        await withTimeout((async () => {
          if (token || refresh) {
            let ok = token ? await refreshAccount() : false
            if (!ok && refresh) {
              const newToken = await tryRefreshToken()
              if (newToken) ok = await refreshAccount()
            }

            if (!ok && !hasStoredCredentials()) {
              clearSession()
            }
          } else if (!hasStoredCredentials()) {
            clearSession()
          }
        })(), 12000, 'Auth restore')
      } catch {
        /* continue as guest — never block the app on auth timeout */
      } finally {
        setLoading(false)
      }
    }
    void init()
  }, [refreshAccount, tryRefreshToken, clearSession])

  const login = useCallback(async (email: string, password: string, rememberMe: boolean) => {
    const result = await api.login(email, password, rememberMe)
    applySession(result.session, rememberMe)
  }, [applySession])

  const register = useCallback(async (
    fullName: string,
    email: string,
    password: string,
    confirm: string,
  ) => {
    const result = await api.register(fullName, email, password, confirm)
    applySession(result.session, true)
  }, [applySession])

  const isLoggedIn = !!user
  const isAdmin = user?.role === 'admin'
  const tier = resolveUserTier(isLoggedIn, license)

  const canAccess = useCallback(
    (feature: AppFeature) => FeatureAccessManager.canAccess(feature, isLoggedIn, license, config),
    [isLoggedIn, license, config],
  )

  const value = useMemo<AuthContextValue>(() => ({
    user,
    license: license ?? guestLicense,
    isLoggedIn,
    isAdmin,
    tier,
    loading,
    login,
    register,
    logout,
    refreshAccount,
    canAccess,
  }), [
    user, license, isLoggedIn, isAdmin, tier, loading,
    login, register, logout, refreshAccount, canAccess,
  ])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export type { PremiumFeature } from './types'
export type { AccessResult } from './features'
