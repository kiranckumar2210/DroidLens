import { useState } from 'react'
import { Eye, EyeOff, X } from 'lucide-react'
import { api } from '../../api/client'
import { useAuth } from '../../auth/AuthContext'

interface Props {
  open: boolean
  onClose: () => void
  onSwitchRegister: () => void
}

export default function LoginModal({ open, onClose, onSwitchRegister }: Props) {
  const { login } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [remember, setRemember] = useState(false)
  const [showPw, setShowPw] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [info, setInfo] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  if (!open) return null

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    setInfo(null)
    try {
      await login(email, password, remember)
      onClose()
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setLoading(false)
    }
  }

  const forgotPassword = async () => {
    if (!email.trim()) {
      setError('Enter your email address first')
      return
    }
    setError(null)
    try {
      const res = await api.forgotPassword(email.trim())
      setInfo(res.message)
    } catch (err) {
      setError((err as Error).message)
    }
  }

  return (
    <div className="auth-overlay" role="dialog" aria-modal="true" aria-label="Sign in">
      <div className="auth-modal">
        <div className="auth-modal-header">
          <h2>Sign In</h2>
          <button type="button" className="btn-icon copy-btn" onClick={onClose} aria-label="Close">
            <X size={16} />
          </button>
        </div>
        <form className="auth-form" onSubmit={submit}>
          {error && <div className="auth-error" role="alert">{error}</div>}
          {info && <div className="auth-error ok">{info}</div>}
          <label className="field-label">Email</label>
          <input type="email" required autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} />
          <label className="field-label">Password</label>
          <div className="auth-password-row">
            <input
              type={showPw ? 'text' : 'password'}
              required
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
            <button type="button" className="btn-icon copy-btn" onClick={() => setShowPw(!showPw)} aria-label="Toggle password">
              {showPw ? <EyeOff size={14} /> : <Eye size={14} />}
            </button>
          </div>
          <div className="auth-forgot-row">
            <label className="auth-checkbox">
              <input type="checkbox" checked={remember} onChange={(e) => setRemember(e.target.checked)} />
              Remember me
            </label>
            <button type="button" className="link-btn" onClick={forgotPassword}>Forgot password?</button>
          </div>
          <button type="submit" className="btn-primary full-width" disabled={loading}>
            {loading ? 'Signing in…' : 'Sign In'}
          </button>
        </form>
        <p className="auth-switch">
          No account?{' '}
          <button type="button" className="link-btn" onClick={onSwitchRegister}>Create one — 7-day free trial</button>
        </p>
      </div>
    </div>
  )
}
