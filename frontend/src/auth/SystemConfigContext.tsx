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
import type { SystemConfig } from './types'

const DEFAULT_CONFIG: SystemConfig = {
  subscription_enabled: false,
  payment_enabled: false,
  trial_enabled: true,
  guest_access_enabled: true,
  login_required_for_live: true,
  trial_days: 7,
  lifetime_price_inr: 199,
  currency: 'INR',
  discount_percent: 0,
  promotional_message: '',
  features: {
    mock_inspector: true,
    live_inspector: true,
    recorder: true,
    xml_upload: true,
    screenshot_upload: true,
    locator_builder: true,
    code_generator: true,
    ai_features: true,
    export: true,
    device_manager: true,
    session_manager: true,
  },
}

interface SystemConfigContextValue {
  config: SystemConfig
  loading: boolean
  refreshConfig: () => Promise<void>
}

const SystemConfigContext = createContext<SystemConfigContextValue | null>(null)

export function useSystemConfig(): SystemConfigContextValue {
  const ctx = useContext(SystemConfigContext)
  if (!ctx) throw new Error('useSystemConfig must be used within SystemConfigProvider')
  return ctx
}

export function SystemConfigProvider({ children }: { children: ReactNode }) {
  const [config, setConfig] = useState<SystemConfig>(DEFAULT_CONFIG)
  const [loading, setLoading] = useState(true)

  const refreshConfig = useCallback(async () => {
    try {
      const data = await api.getSystemConfig()
      setConfig(data)
    } catch {
      setConfig(DEFAULT_CONFIG)
    }
  }, [])

  useEffect(() => {
    void (async () => {
      try {
        await refreshConfig()
      } finally {
        setLoading(false)
      }
    })()
  }, [refreshConfig])

  const value = useMemo(
    () => ({ config, loading, refreshConfig }),
    [config, loading, refreshConfig],
  )

  return (
    <SystemConfigContext.Provider value={value}>
      {children}
    </SystemConfigContext.Provider>
  )
}
