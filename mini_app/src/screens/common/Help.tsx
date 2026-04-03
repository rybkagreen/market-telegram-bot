import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ScreenLayout } from '@/components/layout/ScreenLayout'
import { Notification, Card, Button } from '@/components/ui'
import { useHaptic } from '@/hooks/useHaptic'
import styles from './Help.module.css'

interface FaqItem {
  question: string
  answer: string
}

const ADV_FAQ: FaqItem[] = [
  {
    question: 'Как создать кампанию?',
    answer:
      'Перейдите в меню рекламодателя → «Создать кампанию». Выберите категорию, затем каналы из списка. Введите текст объявления вручную или сгенерируйте через AI. После отправки владелец канала получит заявку и ответит в течение 24 часов.',
  },
  {
    question: 'Как работает эскроу?',
    answer:
      'После того как владелец принял условия, вы оплачиваете размещение — средства замораживаются на платформе. Деньги переводятся владельцу только после подтверждения публикации. Если публикация не состоялась — средства возвращаются вам.',
  },
  {
    question: 'Политика возвратов',
    answer:
      'Отмена до подтверждения владельцем — возврат 100%. Отмена после подтверждения — возврат 50%. Если владелец сам отклонил заявку или произошла техническая ошибка — возврат 100%.',
  },
]

const OWNER_FAQ: FaqItem[] = [
  {
    question: 'Как добавить канал?',
    answer:
      'Добавьте бота @rekharborbot как администратора вашего канала. Затем перейдите в «Мои каналы» → «Добавить канал», введите username или Chat ID. После проверки прав бота выберите категорию канала.',
  },
  {
    question: 'Как получить выплату?',
    answer:
      'Перейдите в «Выплаты» → «Запросить вывод». Укажите сумму (минимум 1 000 ₽) и реквизиты — номер карты или телефон для СБП. Выплаты обрабатываются в течение 24 часов в рабочее время (09:00–22:00 МСК). Комиссия платформы — 1,5%.',
  },
]

function FaqAccordion({ items }: { items: FaqItem[] }) {
  const [openIndex, setOpenIndex] = useState<number | null>(null)
  const haptic = useHaptic()

  const toggle = (i: number) => {
    haptic.tap()
    setOpenIndex(openIndex === i ? null : i)
  }

  return (
    <>
      {items.map((item, i) => (
        <div key={item.question}>
          <button
            className={styles.faqRow}
            onClick={() => toggle(i)}
            aria-expanded={openIndex === i}
          >
            <span>{item.question}</span>
            <span className={styles.chevron}>{openIndex === i ? '∨' : '›'}</span>
          </button>
          {openIndex === i && (
            <p className={styles.faqAnswer}>{item.answer}</p>
          )}
        </div>
      ))}
    </>
  )
}

export default function Help() {
  const navigate = useNavigate()
  const haptic = useHaptic()

  return (
    <ScreenLayout title="Помощь">
      <Notification type="info">Если не нашли ответ — напишите нам!</Notification>

      <Card title="Для рекламодателей" className={styles.card}>
        <FaqAccordion items={ADV_FAQ} />
      </Card>

      <Card title="Для владельцев каналов" className={styles.card}>
        <FaqAccordion items={OWNER_FAQ} />
      </Card>

      <Button
        variant="secondary"
        fullWidth
        onClick={() => {
          haptic.tap()
          navigate('/feedback')
        }}
      >
        ✉️ Написать в поддержку
      </Button>
    </ScreenLayout>
  )
}
