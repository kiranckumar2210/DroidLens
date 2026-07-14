import { useEffect, useMemo, useState } from 'react'
import { ArrowLeft, User } from 'lucide-react'
import { api, isElectron } from '../../api/client'
import { useAuth } from '../../auth/AuthContext'
import { useSystemConfig } from '../../auth/SystemConfigContext'
import type { OrderSummary } from '../../auth/types'

interface Props {
  onBack: () => void
  onOpenSubscription: () => void
}

export default function AccountPage({ onBack, onOpenSubscription }: Props) {
  const { user, license, logout, refreshAccount } = useAuth()
  const { config } = useSystemConfig()
  const showPaymentUi = config.subscription_enabled && config.payment_enabled
  const [name, setName] = useState(user?.full_name ?? '')
  const [msg, setMsg] = useState<string | null>(null)
  const [orders, setOrders] = useState<OrderSummary[]>([])

  useEffect(() => {
    api.getAccount().then((a) => setOrders(a.purchase_history ?? [])).catch(() => {})
  }, [])

  const lifetimeOrder = useMemo(
    () => orders.find((o) => o.status === 'completed' && o.plan_id === 'lifetime'),
    [orders],
  )

  if (!user) return null

  const saveProfile = async () => {
    try {
      await api.updateProfile(name)
      await refreshAccount()
      setMsg('Profile updated')
    } catch (e) {
      setMsg((e as Error).message)
    }
  }

  const trialDays = license?.days_remaining

  return (
    <div className="page-shell account-page">
      <header className="page-shell__header account-header">
        <button type="button" className="back-btn" onClick={onBack}><ArrowLeft size={14} /> Back</button>
        <h1>Account</h1>
      </header>
      <main className="page-shell__body account-body">
        <div className="account-avatar"><User size={40} /></div>
        {msg && <div className="auth-error ok">{msg}</div>}
        <label className="field-label">Full Name</label>
        <input value={name} onChange={(e) => setName(e.target.value)} />
        <button type="button" className="btn-secondary" onClick={saveProfile}>Save Profile</button>

        <div className="account-section">
          <h3>Account Details</h3>
          <Detail label="Name" value={user.full_name} />
          <Detail label="Email" value={user.email} />
          <Detail label="Registered" value={new Date(user.created_at).toLocaleDateString()} />
          <Detail label="License" value={license?.plan_name} />
          {license?.status === 'trial_active' && config.trial_enabled && trialDays != null && (
            <Detail label="Trial Remaining" value={`${trialDays} day${trialDays === 1 ? '' : 's'}`} />
          )}
          <Detail label="Status" value={license?.status.replace(/_/g, ' ')} />
          {license?.trial_expires_at && license.status !== 'lifetime' && (
            <Detail label="Trial Expires" value={new Date(license.trial_expires_at).toLocaleDateString()} />
          )}
          {license?.status === 'lifetime' && (
            <>
              <Detail
                label="Purchase Date"
                value={
                  lifetimeOrder?.completed_at
                    ? new Date(lifetimeOrder.completed_at).toLocaleDateString()
                    : license.license_activated_at
                      ? new Date(license.license_activated_at).toLocaleDateString()
                      : '—'
                }
              />
              <Detail label="Order ID" value={lifetimeOrder?.order_id} />
              <Detail
                label="Transaction Ref"
                value={lifetimeOrder?.phonepe_transaction_id ?? lifetimeOrder?.transaction_id}
              />
            </>
          )}
          <Detail label="App Version" value={isElectron() ? '1.0.0 (Desktop)' : '1.0.0 (Web)'} />
        </div>

        {showPaymentUi && orders.length > 0 && (
          <div className="account-section">
            <h3>Purchase History</h3>
            <div className="purchase-history-table">
              <div className="purchase-history-head">
                <span>Order</span>
                <span>Date</span>
                <span>Amount</span>
                <span>Status</span>
              </div>
              {orders.map((o) => (
                <div key={o.id}>
                  <div className="purchase-history-row">
                    <span className="mono">{o.order_id}</span>
                    <span>{new Date(o.created_at).toLocaleDateString()}</span>
                    <span>₹{o.amount_inr}</span>
                    <span className="capitalize">{o.status}</span>
                  </div>
                  <div className="purchase-history-meta">
                    <span>
                      {o.payment_provider}
                      {o.payment_method ? ` · ${o.payment_method}` : ''}
                      {(o.phonepe_transaction_id || o.transaction_id)
                        ? ` · TXN ${o.phonepe_transaction_id ?? o.transaction_id}`
                        : ''}
                    </span>
                    <span className="purchase-invoice-placeholder">Invoice — coming soon</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="account-actions">
          {showPaymentUi && license?.status !== 'lifetime' && (
            <button type="button" className="btn-primary" onClick={onOpenSubscription}>Upgrade</button>
          )}
          {showPaymentUi && (
            <button type="button" className="btn-secondary" onClick={onOpenSubscription}>Manage License</button>
          )}
          <button type="button" className="btn-secondary" onClick={() => { logout(); onBack() }}>Logout</button>
        </div>
      </main>
    </div>
  )
}

function Detail({ label, value }: { label: string; value?: string | null }) {
  if (!value) return null
  return (
    <div className="detail-row">
      <span>{label}</span>
      <span className="mono">{value}</span>
    </div>
  )
}
