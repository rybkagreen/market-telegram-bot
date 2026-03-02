import { useState, useEffect, useRef } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { billingApi, type InvoiceStatus } from '@/api/billing'

/**
 * Polling статуса CryptoBot инвойса.
 * Проверяет каждые 5 секунд, останавливается при paid/expired/cancelled.
 */
export function useInvoicePolling(invoiceId: string | null) {
  const [status, setStatus] = useState<InvoiceStatus | null>(null)
  const qc = useQueryClient()
  const intervalRef = useRef<number | null>(null)

  useEffect(() => {
    if (!invoiceId) return

    const poll = async () => {
      try {
        const result = await billingApi.checkInvoice(invoiceId)
        setStatus(result)

        if (result.status === 'paid') {
          window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred('success')
          // Обновляем баланс и историю
          qc.invalidateQueries({ queryKey: ['billing', 'balance'] })
          qc.invalidateQueries({ queryKey: ['billing', 'history'] })
          qc.invalidateQueries({ queryKey: ['analytics', 'summary'] })
          if (intervalRef.current) clearInterval(intervalRef.current)
        } else if (['expired', 'cancelled'].includes(result.status)) {
          if (intervalRef.current) clearInterval(intervalRef.current)
        }
      } catch (e) {
        console.error('Invoice polling error:', e)
      }
    }

    poll() // сразу первый вызов
    intervalRef.current = window.setInterval(poll, 5000)

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current)
    }
  }, [invoiceId, qc])

  return status
}
