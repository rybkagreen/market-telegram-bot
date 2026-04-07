import { useNavigate } from 'react-router-dom'
import { Card, Button, Checkbox, Textarea } from '@shared/ui'
import { useState } from 'react'

export default function AdvertiserFrameworkContract() {
  const navigate = useNavigate()
  const [accepted, setAccepted] = useState(false)
  const [comment, setComment] = useState('')

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-display font-bold text-text-primary">Договор рекламодателя</h1>

      <Card title="Рамочный договор на размещение рекламы">
        <div className="space-y-4">
          <div className="bg-harbor-elevated rounded-lg p-4 max-h-64 overflow-y-auto text-sm text-text-secondary leading-relaxed">
            <p className="mb-3">
              Настоящий договор заключается между рекламодателем и платформой RekHarbor
              на размещение рекламных материалов в Telegram-каналах.
            </p>
            <p className="mb-3">
              Платформа выступает посредником между рекламодателем и владельцами каналов,
              обеспечивая безопасную сделку через эскроу-механизм.
            </p>
            <p className="mb-3">
              Комиссия платформы составляет 15% от стоимости размещения. Средства
              резервируются на эскроу-счёте и переводятся владельцу канала после
              успешной публикации.
            </p>
            <p>
              Рекламодатель обязуется предоставить контент, соответствующий требованиям
              законодательства о рекламе и маркировке (ФЗ-38).
            </p>
          </div>

          <Textarea
            rows={3}
            value={comment}
            onChange={setComment}
            placeholder="Комментарий к договору (необязательно)"
          />

          <Checkbox
            checked={accepted}
            onChange={setAccepted}
            label="Я принимаю условия рамочного договора"
          />
        </div>
      </Card>

      <div className="flex flex-col gap-3">
        <Button variant="primary" fullWidth disabled={!accepted} onClick={() => navigate('/legal-profile')}>
          📋 Подписать и перейти к профилю
        </Button>
        <Button variant="secondary" fullWidth onClick={() => navigate('/adv/campaigns')}>
          ← Вернуться к кампаниям
        </Button>
      </div>
    </div>
  )
}
