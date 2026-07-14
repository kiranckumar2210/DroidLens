import { useEffect, useState } from 'react'
import { ArrowLeft, Check } from 'lucide-react'
import { api } from '../../api/client'
import { useAuth } from '../../auth/AuthContext'
import {
  clearCheckoutNavState,
  loadNavState,
  saveNavState,
  type CheckoutStep,
} from '../../auth/navigationStorage'
import { SubscriptionManager } from '../../auth/subscriptionManager'
import type { PlanPublic, PurchaseResult } from '../../auth/types'
import CheckoutPage from './CheckoutPage'
import MockPaymentPage from './MockPaymentPage'
import PaymentStatusPage from './PaymentStatusPage'

interface Props {
  onBack: () => void
  initialPaymentId?: string | null
  initialStep?: CheckoutStep
}

const ACTIVE_ORDER_STATUSES = new Set(['pending', 'created', 'initiated', 'processing'])

export default function SubscriptionPage({ onBack, initialPaymentId, initialStep }: Props) {
  const { license, isLoggedIn, refreshAccount } = useAuth()
  const saved = loadNavState()
  const [plans, setPlans] = useState<PlanPublic[]>([])
  const [lifetimePrice, setLifetimePrice] = useState(199)
  const [paymentProvider, setPaymentProvider] = useState('mock')
  const [step, setStep] = useState<CheckoutStep>(initialStep ?? saved.checkoutStep)
  const [checkout, setCheckout] = useState<PurchaseResult | null>(saved.checkoutSnapshot)
  const [statusPaymentId, setStatusPaymentId] = useState<string | null>(
    initialPaymentId ?? (saved.checkoutStep === 'status' ? saved.paymentId : null),
  )
  const [restoring, setRestoring] = useState(
    Boolean(
      (saved.paymentId || initialPaymentId)
      && (saved.checkoutStep === 'checkout' || saved.checkoutStep === 'payment' || saved.checkoutStep === 'status'),
    ),
  )
  const [loading, setLoading] = useState(false)
  const [msg, setMsg] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const isPhonePe = paymentProvider === 'phonepe'

  useEffect(() => {
    api.listPlans().then(setPlans).catch(() => {})
    api.getPricing().then((p) => {
      setLifetimePrice(p.lifetime_price_inr)
      setPaymentProvider(p.payment_provider)
    }).catch(() => {})
  }, [])

  useEffect(() => {
    saveNavState({
      checkoutStep: step,
      paymentId: statusPaymentId ?? checkout?.payment_id ?? null,
      checkoutSnapshot: checkout,
    })
  }, [step, checkout, statusPaymentId])

  useEffect(() => {
    const paymentId = initialPaymentId ?? saved.paymentId
    if (!paymentId || checkout || !isLoggedIn) {
      setRestoring(false)
      return
    }
    if (initialStep === 'status' || saved.checkoutStep === 'status') {
      setStatusPaymentId(paymentId)
      setStep('status')
      setRestoring(false)
      return
    }
    if (saved.checkoutStep !== 'checkout' && saved.checkoutStep !== 'payment') {
      setRestoring(false)
      return
    }

    void (async () => {
      try {
        const order = await api.getPurchase(paymentId)
        if (ACTIVE_ORDER_STATUSES.has(order.status)) {
          setCheckout(order)
          setStep(saved.checkoutStep)
        } else if (order.status === 'completed') {
          setStatusPaymentId(paymentId)
          setStep('status')
        } else {
          clearCheckoutNavState()
          setStep('plans')
        }
      } catch {
        if (saved.checkoutSnapshot) {
          setCheckout(saved.checkoutSnapshot)
          setStep(saved.checkoutStep)
        } else {
          clearCheckoutNavState()
          setStep('plans')
        }
      } finally {
        setRestoring(false)
      }
    })()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isLoggedIn, initialPaymentId, initialStep])

  const lifetime = plans.find((p) => p.id === 'lifetime')

  const startUpgrade = async () => {
    if (!isLoggedIn) return
    setLoading(true)
    setError(null)
    setMsg(null)
    try {
      const session = await SubscriptionManager.startCheckout('lifetime')
      setCheckout(session)
      setStep('checkout')
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setLoading(false)
    }
  }

  const handlePaymentSuccess = async () => {
    if (!checkout) return
    await SubscriptionManager.completePayment(checkout.payment_id)
    await refreshAccount()
    clearCheckoutNavState()
    setStep('success')
    setMsg('Lifetime License Activated! Thank you for your purchase.')
    setCheckout(null)
  }

  const handlePaymentFailed = async () => {
    if (!checkout) return
    await SubscriptionManager.failPayment(checkout.payment_id)
    await refreshAccount()
    clearCheckoutNavState()
    setCheckout(null)
    setStep('plans')
    setError('Payment failed. Your account was not changed. You can try again.')
  }

  const handlePaymentCancel = async () => {
    if (!checkout) return
    await SubscriptionManager.cancelPayment(checkout.payment_id)
    await refreshAccount()
    clearCheckoutNavState()
    setCheckout(null)
    setStep('plans')
    setMsg(null)
  }

  const backToPlans = async () => {
    if (checkout && !isPhonePe) {
      try {
        await SubscriptionManager.cancelPayment(checkout.payment_id)
        await refreshAccount()
      } catch { /* ignore */ }
    }
    clearCheckoutNavState()
    setStep('plans')
    setCheckout(null)
    setStatusPaymentId(null)
    setError(null)
  }

  if (restoring) {
    return (
      <div className="payment-shell">
        <header className="payment-shell__header account-header">
          <h1>Restoring checkout…</h1>
        </header>
        <main className="payment-shell__body auth-boot-body">
          <p className="auth-boot-text">Loading your order</p>
        </main>
      </div>
    )
  }

  if (step === 'status' && statusPaymentId) {
    return (
      <PaymentStatusPage
        paymentId={statusPaymentId}
        onDashboard={onBack}
        onRetry={() => {
          setStatusPaymentId(null)
          setStep('plans')
          void startUpgrade()
        }}
      />
    )
  }

  if (step === 'checkout' && checkout) {
    return (
      <CheckoutPage
        checkout={checkout}
        paymentProvider={paymentProvider}
        onBack={backToPlans}
        onProceed={() => {
          if (isPhonePe) return
          setStep('payment')
        }}
      />
    )
  }

  if (step === 'payment' && checkout && !isPhonePe) {
    return (
      <MockPaymentPage
        checkout={checkout}
        onBack={() => setStep('checkout')}
        onSuccess={handlePaymentSuccess}
        onFailed={handlePaymentFailed}
        onCancel={handlePaymentCancel}
      />
    )
  }

  return (
    <div className="page-shell subscription-page">
      <header className="page-shell__header account-header">
        <button type="button" className="back-btn" onClick={onBack}><ArrowLeft size={14} /> Back</button>
        <h1>Plans & Licensing</h1>
      </header>
      <main className="page-shell__body subscription-body">
        <div className="subscription-current">
          <h3>Current Plan</h3>
          <p className="plan-name">{license?.plan_name ?? 'Guest'}</p>
          {license?.status === 'trial_active' && (
            <p className="trial-banner">Trial Active — {license.days_remaining} days remaining</p>
          )}
          {license?.status === 'lifetime' && (
            <p className="license-active"><Check size={16} /> Lifetime Activated</p>
          )}
          {license?.status === 'payment_pending' && (
            <p className="payment-pending-banner">⌛ Payment Pending — complete checkout to unlock premium</p>
          )}
          {license?.status === 'trial_expired' && (
            <p className="auth-error">Your trial has expired. Purchase a license to continue.</p>
          )}
        </div>

        {msg && <div className="auth-error ok">{msg}</div>}
        {error && <div className="auth-error" role="alert">{error}</div>}

        <div className="plan-cards">
          {lifetime && (
            <article className="plan-card featured">
              <h3>{lifetime.name}</h3>
              <p className="plan-desc">{lifetime.description}</p>
              <p className="plan-price">₹{lifetime.price_inr ?? lifetimePrice} <span>one-time</span></p>
              <ul className="plan-features">
                <li>Live Device Inspection</li>
                <li>XML & Screenshot Upload</li>
                <li>Code Generator & Locator Builder</li>
                <li>Locator Repository & Export</li>
                <li>All future premium features</li>
              </ul>
              {license?.status !== 'lifetime' && isLoggedIn && (
                <button type="button" className="btn-primary full-width" disabled={loading} onClick={startUpgrade}>
                  {loading ? 'Preparing checkout…' : `Upgrade to Lifetime — ₹${lifetimePrice}`}
                </button>
              )}
              {license?.status === 'lifetime' && (
                <p className="plan-owned">You own this plan</p>
              )}
            </article>
          )}

          <article className="plan-card future">
            <h3>Coming Soon</h3>
            <p className="plan-desc">Monthly, Yearly, Team & Enterprise plans</p>
            <ul className="plan-features muted">
              <li>Monthly subscription</li>
              <li>Yearly subscription</li>
              <li>Team licenses</li>
              <li>Enterprise & Education</li>
            </ul>
          </article>
        </div>

        <section className="subscription-faq">
          <h3>FAQ</h3>
          <details><summary>When is premium access granted?</summary>
            <p>
              {isPhonePe
                ? 'Only after PhonePe confirms payment and our server verifies the transaction via webhook. Redirecting to checkout alone does not unlock premium.'
                : 'Only after you complete the mock payment flow and select Payment Successful. Clicking Upgrade alone does not unlock premium features.'}
            </p>
          </details>
          <details><summary>What happens after the 7-day trial?</summary>
            <p>Premium features lock until you purchase a Lifetime License. Your account and saved data remain intact.</p>
          </details>
          <details><summary>Is the Lifetime License really one-time?</summary>
            <p>Yes — ₹{lifetimePrice} one-time payment for lifetime access to all current premium features.</p>
          </details>
        </section>
      </main>
    </div>
  )
}
