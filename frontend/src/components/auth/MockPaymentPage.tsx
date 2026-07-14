import { useState } from 'react'
import { ArrowLeft, CheckCircle, XCircle } from 'lucide-react'
import type { PurchaseResult } from '../../auth/types'

interface Props {
  checkout: PurchaseResult
  onBack: () => void
  onSuccess: () => Promise<void>
  onFailed: () => Promise<void>
  onCancel: () => Promise<void>
}

export default function MockPaymentPage({ checkout, onBack, onSuccess, onFailed, onCancel }: Props) {
  const [loading, setLoading] = useState<'success' | 'fail' | 'cancel' | null>(null)
  const [error, setError] = useState<string | null>(null)

  const run = async (action: 'success' | 'fail' | 'cancel') => {
    setLoading(action)
    setError(null)
    try {
      if (action === 'success') await onSuccess()
      else if (action === 'fail') await onFailed()
      else await onCancel()
    } catch (e) {
      setError((e as Error).message)
      setLoading(null)
    }
  }

  return (
    <div className="payment-shell mock-gateway">
      <header className="payment-shell__header account-header">
        <button type="button" className="back-btn" onClick={onBack} disabled={!!loading}>
          <ArrowLeft size={14} /> Back
        </button>
        <h1>Mock Payment Gateway</h1>
      </header>

      <main className="payment-shell__body">
        <div className="mock-gateway-card">
          <p className="mock-merchant">{checkout.merchant_name}</p>
          <h2>Complete Your Payment</h2>

          <div className="mock-details">
            <div className="detail-row">
              <span>Order ID</span>
              <span className="mono checkout-mono">{checkout.order_id}</span>
            </div>
            <div className="detail-row">
              <span>Transaction ID</span>
              <span className="mono checkout-mono">{checkout.transaction_id}</span>
            </div>
            <div className="detail-row">
              <span>Amount</span>
              <strong>₹{checkout.amount_inr}</strong>
            </div>
            <div className="detail-row">
              <span>Customer</span>
              <span className="checkout-email">{checkout.customer_email}</span>
            </div>
            <div className="detail-row">
              <span>Product</span>
              <span>{checkout.plan_name}</span>
            </div>
            <div className="detail-row">
              <span>Status</span>
              <span className="capitalize">{checkout.status}</span>
            </div>
          </div>

          <p className="mock-hint">
            This is a development mock gateway. Select an outcome to simulate payment processing.
          </p>

          {error && <div className="auth-error" role="alert">{error}</div>}
        </div>
      </main>

      <footer className="payment-shell__footer">
        <button
          type="button"
          className="btn-primary full-width mock-success"
          disabled={!!loading}
          onClick={() => run('success')}
        >
          <CheckCircle size={16} />
          {loading === 'success' ? 'Processing…' : 'Payment Successful'}
        </button>
        <button
          type="button"
          className="btn-secondary full-width mock-fail"
          disabled={!!loading}
          onClick={() => run('fail')}
        >
          <XCircle size={16} />
          {loading === 'fail' ? 'Processing…' : 'Payment Failed'}
        </button>
        <button
          type="button"
          className="btn-ghost full-width"
          disabled={!!loading}
          onClick={() => run('cancel')}
        >
          {loading === 'cancel' ? 'Cancelling…' : '↩ Cancel Payment'}
        </button>
      </footer>
    </div>
  )
}
