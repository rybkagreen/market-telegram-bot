import { useState } from 'react'
import { Modal } from './Modal'
import { Button } from './Button'
import { Notification } from './Notification'
import type { PaymentProviderErrorDetail } from '@/lib/types'
import styles from './PaymentErrorModal.module.css'

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
        <div className={styles.body}>
          <Notification type="warning">{error.message}</Notification>
          <div className={styles.requestBlock}>
            <div className={styles.requestLabel}>Код запроса</div>
            <div className={styles.requestRow}>
              <code className={styles.requestId}>{error.provider_request_id}</code>
              <button type="button" className={styles.copyBtn} onClick={handleCopy}>
                {copied ? '✓ Скопировано' : '📋 Копировать'}
              </button>
            </div>
          </div>
          <p className={styles.hint}>
            Если проблема повторяется — отправьте код запроса в поддержку, чтобы быстрее найти причину.
          </p>
        </div>
      )}
    </Modal>
  )
}
