import { useCallback, useState } from 'react'
import type { AppFeature } from '../auth/types'
import type { AccessResult } from '../auth/features'
import { useAuth } from './AuthContext'

export function usePremiumGate() {
  const { canAccess } = useAuth()
  const [gateOpen, setGateOpen] = useState(false)
  const [gateAccess, setGateAccess] = useState<AccessResult | null>(null)

  const requestFeature = useCallback((feature: AppFeature, action: () => void | Promise<void>) => {
    const access = canAccess(feature)
    if (access.allowed) {
      void action()
      return true
    }
    setGateAccess(access)
    setGateOpen(true)
    return false
  }, [canAccess])

  const closeGate = useCallback(() => {
    setGateOpen(false)
    setGateAccess(null)
  }, [])

  return { gateOpen, gateAccess, requestFeature, closeGate }
}
