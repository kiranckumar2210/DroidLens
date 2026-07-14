import type { LicenseInfo, OrderStatusResponse, PurchaseResult } from './types'
import { api } from '../api/client'

/** UI-facing payment orchestration — swap mock/real gateway via API client only. */
export class SubscriptionManager {
  static async startCheckout(planId: string): Promise<PurchaseResult> {
    return api.createPurchase(planId)
  }

  static async getCheckout(paymentId: string): Promise<PurchaseResult> {
    return api.getPurchase(paymentId)
  }

  static async syncPaymentStatus(paymentId: string): Promise<OrderStatusResponse> {
    return api.syncPaymentStatus(paymentId)
  }

  static async completePayment(paymentId: string): Promise<LicenseInfo> {
    const result = await api.confirmPurchase(paymentId)
    return result.license
  }

  static async failPayment(paymentId: string): Promise<LicenseInfo> {
    const result = await api.failPurchase(paymentId)
    return result.license
  }

  static async cancelPayment(paymentId: string): Promise<LicenseInfo> {
    const result = await api.cancelPurchase(paymentId)
    return result.license
  }
}
