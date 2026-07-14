import { ArrowLeft } from 'lucide-react'
import type { PurchaseResult } from '../../auth/types'

interface Props {
  checkout: PurchaseResult
  paymentProvider?: string
  onBack: () => void
  onProceed: () => void
}

const FEATURES = [
  'Live Device Inspection',
  'XML Upload',
  'Screenshot Upload',
  'Code Generator',
  'Locator Builder',
  'Export & Premium Updates',
]

export default function CheckoutPage({ checkout, paymentProvider, onBack, onProceed }: Props) {
  const isPhonePe = Boolean(
    checkout.checkout_url
    && (checkout.payment_provider === 'phonepe' || paymentProvider === 'phonepe'),
  )

  const handleProceed = () => {
    if (isPhonePe && checkout.checkout_url) {
      window.location.href = checkout.checkout_url
      return
    }
    onProceed()
  }

  return (
    <div className="payment-shell">
      <header className="payment-shell__header account-header">
        <button type="button" className="back-btn" onClick={onBack}>
          <ArrowLeft size={14} /> Back
        </button>
        <h1>Checkout</h1>
      </header>

      <main className="payment-shell__body">
        <div className="checkout-card">
          <div className="checkout-divider">DroidLens Lifetime License</div>
          <h2>{checkout.plan_name}</h2>
          <p className="checkout-subtitle">Lifetime Access</p>

          <div className="checkout-price-row">
            <span>Price</span>
            <strong>₹{checkout.amount_inr}</strong>
          </div>

          <h3 className="checkout-section">Features Included</h3>
          <ul className="checkout-features">
            {FEATURES.map((f) => (
              <li key={f}>✔ {f}</li>
            ))}
          </ul>

          <div className="checkout-summary">
            <h3>Order Summary</h3>
            <div className="detail-row">
              <span>Order ID</span>
              <span className="mono checkout-mono">{checkout.order_id}</span>
            </div>
            <div className="detail-row">
              <span>Email</span>
              <span className="checkout-email">{checkout.customer_email}</span>
            </div>
            <div className="detail-row">
              <span>Payment</span>
              <span>{isPhonePe ? 'PhonePe Secure Checkout' : checkout.merchant_name}</span>
            </div>
            <div className="detail-row">
              <span>Total</span>
              <strong>₹{checkout.amount_inr} (one-time)</strong>
            </div>
          </div>

          <p className="checkout-terms">
            {isPhonePe
              ? 'You will be redirected to PhonePe to complete payment securely. Premium access is granted only after payment verification.'
              : 'By proceeding you agree to the DroidLens purchase terms. Premium access is granted only after successful payment confirmation.'}
          </p>
        </div>
      </main>

      <footer className="payment-shell__footer">
        <button type="button" className="btn-primary full-width" onClick={handleProceed}>
          {isPhonePe ? 'Continue to PhonePe' : 'Proceed to Payment'}
        </button>
        <button type="button" className="btn-secondary full-width" onClick={onBack}>
          Cancel
        </button>
      </footer>
    </div>
  )
}
