/** Persist navigation overlay and checkout flow across browser refresh. */

import type { PurchaseResult } from './types'

export type AuthOverlay = 'none' | 'login' | 'register' | 'account' | 'subscription'
export type CheckoutStep = 'plans' | 'checkout' | 'payment' | 'success' | 'status'

interface NavState {
  authOverlay: AuthOverlay
  checkoutStep: CheckoutStep
  paymentId: string | null
  checkoutSnapshot: PurchaseResult | null
}

const KEY = 'droidlens-nav-state-v1'

function defaultState(): NavState {
  return {
    authOverlay: 'none',
    checkoutStep: 'plans',
    paymentId: null,
    checkoutSnapshot: null,
  }
}

export function loadNavState(): NavState {
  try {
    const raw = sessionStorage.getItem(KEY) ?? localStorage.getItem(KEY)
    if (!raw) return defaultState()
    return { ...defaultState(), ...JSON.parse(raw) }
  } catch {
    return defaultState()
  }
}

export function saveNavState(patch: Partial<NavState>): void {
  try {
    const next = { ...loadNavState(), ...patch }
    const json = JSON.stringify(next)
    sessionStorage.setItem(KEY, json)
    localStorage.setItem(KEY, json)
  } catch {
    /* quota or private mode */
  }
}

export function clearCheckoutNavState(): void {
  saveNavState({ checkoutStep: 'plans', paymentId: null, checkoutSnapshot: null })
}

export function saveAuthOverlay(overlay: AuthOverlay): void {
  saveNavState({ authOverlay: overlay })
}
