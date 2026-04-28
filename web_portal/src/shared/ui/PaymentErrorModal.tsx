import { useState } from 'react'
import { Modal } from './Modal'
import { Button } from './Button'
import { Notification } from './Notification'
import type { PaymentProviderErrorDetail } from '@/lib/types'

interface PaymentErrorModalProps {
  open: boolean
  onClose: () => void
  error: PaymentProviderErrorDetail | null
}

export function PaymentErrorModal({ open, onClose, error }: PaymentErrorModalProps) {
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    if (!error) return
    try {
      await navigator.clipboard.writeText(error.provider_request_id)
      setCopied(true)
      window.setTimeout(() => setCopied(false), 2000)
    } catch {
      setCopied(false)
    }
  }

  return (
    <Modal
      open={open && error !== null}
      onClose={onClose}
      title="Платёжный сервис недоступен"
      footer={
        <Button variant="primary" fullWidth onClick={onClose}>
          Понятно
        </Button>
      }
    >
      {error && (
        <div className="flex flex-col gap-3.5">
          <Notification type="warning">{error.message}</Notification>

          <div className="flex flex-col gap-1.5 bg-harbor-elevated border border-border rounded-md px-4 py-3">
            <div className="text-[11px] font-semibold uppercase tracking-wider text-text-tertiary">
              Код запроса
            </div>
            <div className="flex items-center gap-2 flex-wrap">
              <code className="flex-1 min-w-0 font-mono text-sm text-text-primary break-all">
                {error.provider_request_id}
              </code>
              <button
                type="button"
                onClick={handleCopy}
                className="flex-shrink-0 px-3 py-1.5 rounded-md border border-border bg-harbor-card text-text-primary text-xs font-medium hover:border-border-active transition-colors"
              >
                {copied ? '✓ Скопировано' : '📋 Копировать'}
              </button>
            </div>
          </div>

          <p className="text-xs text-text-secondary leading-relaxed m-0">
            Если проблема повторяется — отправьте код запроса в поддержку, чтобы быстрее найти причину.
          </p>
        </div>
      )}
    </Modal>
  )
}
