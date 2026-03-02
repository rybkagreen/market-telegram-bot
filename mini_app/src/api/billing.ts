import { apiClient } from './client'

export interface PackageInfo {
  id: string
  credits: number
  bonus: number
  total_credits: number
  label: string
  usdt_approx: number
}

export interface BalanceData {
  credits: number
  plan: 'free' | 'starter' | 'pro' | 'business'
  plan_expires_at: string | null
  ai_generations_used: number
  ai_included: number
  packages: PackageInfo[]
  plan_costs: Record<string, number>
}

export interface PaymentHistoryItem {
  id: number
  method: 'cryptobot' | 'stars'
  currency: string | null
  credits: number
  bonus_credits: number
  status: 'pending' | 'paid' | 'expired' | 'cancelled'
  created_at: string
}

export interface HistoryData {
  items: PaymentHistoryItem[]
  total: number
  page: number
  pages: number
}

export interface CryptoInvoice {
  pay_url: string
  invoice_id: string
  credits: number
  bonus_credits: number
  amount: string
  currency: string
}

export interface StarsInvoice {
  invoice_link: string
  credits: number
  bonus_credits: number
  stars_amount: number
}

export interface PlanResult {
  success: boolean
  plan: string
  credits_remaining: number
  message: string
}

export interface InvoiceStatus {
  invoice_id: string
  status: 'pending' | 'paid' | 'expired' | 'cancelled'
  credits: number
  credited: boolean
}

export const billingApi = {
  balance: (): Promise<BalanceData> =>
    apiClient.get('/billing/balance').then(r => r.data),

  history: (page = 1): Promise<HistoryData> =>
    apiClient.get(`/billing/history?page=${page}`).then(r => r.data),

  createCryptoInvoice: (packageId: string, currency: string): Promise<CryptoInvoice> =>
    apiClient.post('/billing/topup/crypto', {
      package_id: packageId, currency,
    }).then(r => r.data),

  createStarsInvoice: (packageId: string): Promise<StarsInvoice> =>
    apiClient.post('/billing/topup/stars', { package_id: packageId }).then(r => r.data),

  changePlan: (plan: string): Promise<PlanResult> =>
    apiClient.post('/billing/plan', { plan }).then(r => r.data),

  checkInvoice: (invoiceId: string): Promise<InvoiceStatus> =>
    apiClient.get(`/billing/invoice/${invoiceId}`).then(r => r.data),
}
