import { useState } from 'react'
import { Eye, EyeOff, X } from 'lucide-react'
import { useAuth } from '../../auth/AuthContext'

interface Props {
  open: boolean
  onClose: () => void
  onSwitchLogin: () => void
}

export default function RegisterModal({ open, onClose, onSwitchLogin }: Props) {
  const { register } = useAuth()
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [showPw, setShowPw] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  if (!open) return null

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (password !== confirm) {
      setError('Passwords do not match')
      return
    }
    setLoading(true)
    setError(null)
    try {
      await register(fullName, email, password, confirm)
      onClose()
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-overlay" role="dialog" aria-modal="true" aria-label="Create account">
      <div className="auth-modal">
        <div className="auth-modal-header">
          <h2>Create Account</h2>
          <button type="button" className="btn-icon copy-btn" onClick={onClose} aria-label="Close">
            <X size={16} />
          </button>
        </div>
        <p className="auth-trial-note">Start your <strong>7-day free trial</strong> — full access to all premium features.</p>
        <form className="auth-form" onSubmit={submit}>
          {error && <div className="auth-error" role="alert">{error}</div>}
          <label className="field-label">Full Name</label>
          <input required value={fullName} onChange={(e) => setFullName(e.target.value)} autoComplete="name" />
          <label className="field-label">Email</label>
          <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" />
          <label className="field-label">Password</label>
          <div className="auth-password-row">
            <input
              type={showPw ? 'text' : 'password'}
              required
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="new-password"
            />
            <button type="button" className="btn-icon copy-btn" onClick={() => setShowPw(!showPw)}>
              {showPw ? <EyeOff size={14} /> : <Eye size={14} />}
            </button>
          </div>
          <p className="auth-hint">Min 8 chars, uppercase, lowercase, and a digit.</p>
          <label className="field-label">Confirm Password</label>
          <input type="password" required value={confirm} onChange={(e) => setConfirm(e.target.value)} autoComplete="new-password" />
          <button type="submit" className="btn-primary full-width" disabled={loading}>
            {loading ? 'Creating…' : 'Create Account & Start Trial'}
          </button>
        </form>
        <p className="auth-switch">
          Already have an account?{' '}
          <button type="button" className="link-btn" onClick={onSwitchLogin}>Sign in</button>
        </p>
      </div>
    </div>
  )
}
