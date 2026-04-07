import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, Button, Notification } from '@shared/ui'

interface FaqItem {
  question: string
  answer: string
}

const ADV_FAQ: FaqItem[] = [
  {
    question: 'Как создать кампанию?',
    answer: 'Перейдите в «Кампании» → «Создать». Выберите категорию, каналы, формат и текст. Отправьте заявку владельцу канала.',
  },
  {
    question: 'Как работает эскроу?',
    answer: 'После оплаты средства замораживаются на платформе и переводятся владельцу только после публикации. Если публикация не состоялась — возврат 100%.',
  },
  {
    question: 'Политика возвратов',
    answer: 'До подтверждения — возврат 100%. После подтверждения — 50%. Если владелец отклонил — 100%.',
  },
]

const OWNER_FAQ: FaqItem[] = [
  {
    question: 'Как добавить канал?',
    answer: 'Добавьте бота @RekHarborBot как администратора канала. Затем «Каналы» → «Добавить» и введите username или Chat ID.',
  },
  {
    question: 'Как получить выплату?',
    answer: '«Выплаты» → «Запросить вывод». Мин. 1 000 ₽. Обработка 24 часа, 09:00–22:00 МСК. Комиссия 1,5%.',
  },
]

function FaqAccordion({ items }: { items: FaqItem[] }) {
  const [openIndex, setOpenIndex] = useState<number | null>(null)

  return (
    <div className="space-y-2">
      {items.map((item, i) => (
        <div key={item.question} className="border border-border rounded-lg overflow-hidden">
          <button
            className="w-full flex items-center justify-between px-4 py-3 text-left text-sm font-medium text-text-primary hover:bg-harbor-elevated transition-colors"
            onClick={() => setOpenIndex(openIndex === i ? null : i)}
          >
            <span>{item.question}</span>
            <span className="text-text-tertiary transition-transform">{openIndex === i ? '▾' : '▸'}</span>
          </button>
          {openIndex === i && (
            <div className="px-4 pb-3 text-sm text-text-secondary leading-relaxed">
              {item.answer}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}

export default function Help() {
  const navigate = useNavigate()

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-display font-bold text-text-primary">Помощь</h1>

      <Notification type="info">Не нашли ответ? Напишите нам!</Notification>

      <Card title="Для рекламодателей">
        <FaqAccordion items={ADV_FAQ} />
      </Card>

      <Card title="Для владельцев каналов">
        <FaqAccordion items={OWNER_FAQ} />
      </Card>

      <Button variant="secondary" fullWidth onClick={() => navigate('/feedback')}>
        ✉️ Написать в поддержку
      </Button>
    </div>
  )
}
