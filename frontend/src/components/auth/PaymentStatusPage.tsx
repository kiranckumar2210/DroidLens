import { useCallback, useEffect, useState } from 'react'
import { ArrowLeft, CheckCircle, RefreshCw, XCircle } from 'lucide-react'
import { useAuth } from '../../auth/AuthContext'
import { SubscriptionManager } from '../../auth/subscriptionManager'
import type { OrderStatusResponse } from '../../auth/types'
import { clearCheckoutNavState } from '../../auth/navigationStorage'

interface Props {
  paymentId: string
  onDashboard: () => void
  onRetry: () => void
}

const TERMINAL = new Set(['completed', 'failed', 'cancelled', 'refunded'])

export default function PaymentStatusPage({ paymentId, onDashboard, onRetry }: Props) {
  const { refreshAccount } = useAuth()
  const [status, setStatus] = useState<OrderStatusResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [polls, setPolls] = useState(0)

  const sync = useCallback(async () => {
    setError(null)
    try {
      const result = await SubscriptionManager.syncPaymentStatus(paymentId)
      setStatus(result)
      await refreshAccount()
      if (TERMINAL.has(result.status)) {
        clearCheckoutNavState()
      }
      return result
    } catch (e) {
      setError((e as Error).message)
      return null
    } finally {
      setLoading(false)
    }
  }, [paymentId, refreshAccount])

  useEffect(() => {
    void sync()
  }, [sync])

  useEffect(() => {
    if (!status || TERMINAL.has(status.status) || polls >= 8) return
    const timer = window.setTimeout(() => {
      setPolls((p) => p + 1)
      void sync()
    }, 2500)
    return () => window.clearTimeout(timer)
  }, [status, polls, sync])

  const isSuccess = status?.status === 'completed' || status?.license.status === 'lifetime'
  const isFailed = status?.status === 'failed'
  const isCancelled = status?.status === 'cancelled'
  const isPending = status && !TERMINAL.has(status.status)

  return (
    <div className="payment-shell">
      <header className="payment-shell__header account-header">
        <button type="button" className="back-btn" onClick={onDashboard}>
          <ArrowLeft size={14} /> Dashboard
        </button>
        <h1>Payment Status</h1>
      </header>

      <main className="payment-shell__body">
        <div className="checkout-card payment-status-card">
          {loading && !status && (
            <p className="auth-boot-text"><RefreshCw size={16} className="spin" /> Verifying payment with PhonePe…</p>
          )}
          {error && <div className="auth-error" role="alert">{error}</div>}

          {isSuccess && (
            <>
              <div className="payment-status-icon success"><CheckCircle size={48} /></div>
              <h2>Payment Successful</h2>
              <p className="checkout-subtitle">Lifetime License Activated</p>
              {status?.phonepe_transaction_id && (
                <div className="detail-row">
                  <span>Transaction</span>
                  <span className="mono checkout-mono">{status.phonepe_transaction_id}</span>
                </div>
              )}
              <div className="detail-row">
                <span>Order ID</span>
                <span className="mono checkout-mono">{status?.order_id}</span>
              </div>
            </>
          )}

          {isFailed && (
            <>
              <div className="payment-status-icon failed"><XCircle size={48} /></div>
              <h2>Payment Failed</h2>
              <p className="checkout-terms">Your account was not charged for premium access. You can retry the payment.</p>
            </>
          )}

          {isCancelled && (
            <>
              <div className="payment-status-icon failed"><XCircle size={48} /></div>
              <h2>Payment Cancelled</h2>
              <p className="checkout-terms">No changes were made to your license. Your trial remains active if applicable.</p>
            </>
          )}

          {isPending && (
            <>
              <div className="payment-status-icon pending"><RefreshCw size={48} className="spin" /></div>
              <h2>Processing Payment</h2>
              <p className="checkout-terms">
                Waiting for PhonePe confirmation. This page will update automatically.
              </p>
              <p className="mono checkout-mono">Status: {status.status}</p>
            </>
          )}
        </div>
      </main>

      <footer className="payment-shell__footer">
        {isSuccess && (
          <button type="button" className="btn-primary full-width" onClick={onDashboard}>
            Go to Dashboard
          </button>
        )}
        {(isFailed || isCancelled) && (
          <>
            <button type="button" className="btn-primary full-width" onClick={onRetry}>
              Retry Payment
            </button>
            <button type="button" className="btn-secondary full-width" onClick={onDashboard}>
              Return to Dashboard
            </button>
          </>
        )}
        {isPending && (
          <button type="button" className="btn-secondary full-width" onClick={() => void sync()}>
            Refresh Status
          </button>
        )}
      </footer>
    </div>
  )
}
