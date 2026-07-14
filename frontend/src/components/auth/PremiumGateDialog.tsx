import { useEffect, useState } from 'react'
import { Lock, X } from 'lucide-react'
import { api } from '../../api/client'
import type { AccessResult } from '../../auth/features'

interface Props {
  open: boolean
  access: AccessResult | null
  onClose: () => void
  onSignIn: () => void
  onRegister: () => void
  onSubscribe: () => void
}

export default function PremiumGateDialog({
  open, access, onClose, onSignIn, onRegister, onSubscribe,
}: Props) {
  const [lifetimePrice, setLifetimePrice] = useState(199)

  useEffect(() => {
    api.getPricing().then((p) => setLifetimePrice(p.lifetime_price_inr)).catch(() => {})
  }, [])

  if (!open || !access || access.allowed) return null

  const isExpired = access.reason === 'trial_expired'

  return (
    <div className="auth-overlay" role="dialog" aria-modal="true">
      <div className="auth-modal premium-gate">
        <div className="auth-modal-header">
          <h2><Lock size={18} /> Premium Feature</h2>
          <button type="button" className="btn-icon copy-btn" onClick={onClose}><X size={16} /></button>
        </div>
        <p className="premium-gate-msg">{access.message}</p>
        <div className="premium-gate-actions">
          {!isExpired && (
            <>
              <button type="button" className="btn-primary" onClick={() => { onClose(); onRegister() }}>
                Create Account — Free Trial
              </button>
              <button type="button" className="btn-secondary" onClick={() => { onClose(); onSignIn() }}>
                Sign In
              </button>
            </>
          )}
          {isExpired && (
            <button type="button" className="btn-primary" onClick={() => { onClose(); onSubscribe() }}>
              Get Lifetime License — ₹{lifetimePrice}
            </button>
          )}
          <button type="button" className="btn-ghost" onClick={onClose}>Continue as Guest</button>
        </div>
      </div>
    </div>
  )
}
