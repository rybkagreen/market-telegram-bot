import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Button,
  Checkbox,
  Textarea,
  Icon,
  ScreenHeader,
  Notification,
} from '@shared/ui'

export default function AdvertiserFrameworkContract() {
  const navigate = useNavigate()
  const [accepted, setAccepted] = useState(false)
  const [comment, setComment] = useState('')

  return (
    <div className="max-w-[1080px] mx-auto">
      <ScreenHeader
        title="Рамочный договор рекламодателя"
        subtitle="Подпишите однократно — далее вы сможете размещать рекламу без дополнительных подтверждений."
        action={
          <Button variant="ghost" size="sm" iconLeft="external">
            Скачать PDF
          </Button>
        }
      />

      <div className="grid gap-5 lg:grid-cols-[1fr_320px]">
        <div className="bg-harbor-card border border-border rounded-xl overflow-hidden">
          <div className="px-5 py-3 border-b border-border bg-harbor-secondary flex items-center gap-2">
            <Icon name="contract" size={14} className="text-text-tertiary" />
            <span className="font-display text-[13px] font-semibold text-text-primary">
              Текст договора
            </span>
          </div>
          <div className="p-5 max-h-[52vh] overflow-y-auto text-[13.5px] leading-[1.6] text-text-secondary space-y-3">
            <p>
              Настоящий договор заключается между рекламодателем и платформой RekHarbor
              на размещение рекламных материалов в Telegram-каналах.
            </p>
            <p>
              Платформа выступает посредником между рекламодателем и владельцами каналов,
              обеспечивая безопасную сделку через эскроу-механизм. Средства рекламодателя
              резервируются на эскроу-счёте и переводятся владельцу канала только после
              подтверждения публикации поста.
            </p>
            <p>
              Комиссия платформы составляет <strong className="text-text-primary">15%</strong> от
              стоимости размещения. Оставшиеся 85% переводятся владельцу канала.
            </p>
            <p>
              Рекламодатель обязуется предоставить контент, соответствующий требованиям
              Федерального закона № 38-ФЗ «О рекламе» и правилам маркировки (ФЗ-38).
              Все рекламные материалы проходят обязательную маркировку у аккредитованного
              ОРД-оператора.
            </p>
            <p>
              Спорные случаи разрешаются через встроенный механизм арбитража платформы.
              Рекламодатель имеет право открыть спор в течение 48 часов с момента публикации.
            </p>
          </div>
        </div>

        <div className="space-y-4">
          <div className="bg-harbor-card border border-border rounded-xl p-5">
            <div className="font-display text-[14px] font-semibold text-text-primary mb-3">
              Комментарий
            </div>
            <Textarea
              rows={3}
              value={comment}
              onChange={setComment}
              placeholder="Необязательный комментарий к договору"
            />
          </div>

          <div className="bg-harbor-card border border-border rounded-xl p-5">
            <Checkbox
              checked={accepted}
              onChange={setAccepted}
              label="Я принимаю условия рамочного договора"
            />
            {!accepted && (
              <div className="mt-3">
                <Notification type="info">
                  Отметьте согласие, чтобы подписать договор и перейти к настройке профиля.
                </Notification>
              </div>
            )}
          </div>

          <div className="flex flex-col gap-2.5">
            <Button
              variant="primary"
              fullWidth
              iconLeft="check"
              disabled={!accepted}
              onClick={() => navigate('/legal-profile')}
            >
              Подписать и продолжить
            </Button>
            <Button
              variant="secondary"
              fullWidth
              iconLeft="arrow-left"
              onClick={() => navigate('/adv/campaigns')}
            >
              Вернуться к кампаниям
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}
