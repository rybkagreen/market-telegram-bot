import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'motion/react'
import { ChevronDown } from 'lucide-react'
import {
  BOT_URL,
  OWNER_SHARE_EFFECTIVE,
  PLATFORM_COMMISSION_EFFECTIVE,
  PLATFORM_COMMISSION_GROSS,
  SERVICE_FEE,
  YOOKASSA_FEE,
  PAYOUT_FEE,
  formatRatePct,
} from '../lib/constants'

const COMMISSION_PCT = formatRatePct(PLATFORM_COMMISSION_EFFECTIVE)
const OWNER_SHARE = formatRatePct(OWNER_SHARE_EFFECTIVE)
const COMMISSION_GROSS_PCT = formatRatePct(PLATFORM_COMMISSION_GROSS, 0)
const SERVICE_FEE_PCT = formatRatePct(SERVICE_FEE)
const YOOKASSA_FEE_PCT = formatRatePct(YOOKASSA_FEE)
const PAYOUT_FEE_PCT = formatRatePct(PAYOUT_FEE)

const FAQ_ITEMS = [
  {
    q: 'Как работает эскроу?',
    a: `После оплаты рекламодателем деньги блокируются на счёте платформы. Владелец канала получает выплату только после подтверждения публикации. Если размещение не состоялось — возврат 100% до начала публикации или 50% после.`,
  },
  {
    q: 'Что такое ОРД и зачем это нужно?',
    a: `Оператор Рекламных Данных — обязательная государственная система учёта интернет-рекламы. RekHarbor автоматически регистрирует каждое размещение в Яндекс ОРД и добавляет erid-маркировку в пост. Вам не нужно разбираться в этом самостоятельно.`,
  },
  {
    q: 'Сколько стоит комиссия платформы?',
    a: `${COMMISSION_PCT} от суммы сделки удерживает платформа (${COMMISSION_GROSS_PCT} комиссия + ${SERVICE_FEE_PCT} сервисный сбор из доли владельца). Владелец канала получает ${OWNER_SHARE} стоимости размещения. Дополнительно: пополнение баланса — ${YOOKASSA_FEE_PCT} (pass-through ЮKassa); комиссия за вывод — ${PAYOUT_FEE_PCT}.`,
  },
  {
    q: 'Как владелец канала получает выплаты?',
    a: `Автоматически после подтверждения завершения размещения (удаления поста по расписанию). Средства зачисляются на баланс, вывод — через YooKassa.`,
  },
  {
    q: 'Можно ли отказаться от заявки?',
    a: `Да, владелец может отклонить заявку или предложить другую цену (до 3 раундов торга). За необоснованные отказы начисляются штрафные баллы репутации.`,
  },
  {
    q: 'Что такое система репутации?',
    a: `Каждый пользователь имеет рейтинг от 0.0 до 10.0 (начальный: 5.0). Нарушения снижают рейтинг, 30 дней без нарушений — восстанавливают. При критически низком рейтинге — временная блокировка.`,
  },
  {
    q: 'Нужно ли устанавливать что-то дополнительно?',
    a: `Нет. Всё работает через Telegram-бот @RekHarborBot. Владельцам каналов нужно только выдать боту права администратора.`,
  },
  {
    q: 'Есть ли веб-интерфейс?',
    a: `Да, веб-портал доступен на portal.rekharbor.ru для расширенного управления кампаниями и аналитики.`,
  },
] as const

function buildFaqSchema() {
  return {
    '@context': 'https://schema.org',
    '@type': 'FAQPage',
    mainEntity: FAQ_ITEMS.map(({ q, a }) => ({
      '@type': 'Question',
      name: q,
      acceptedAnswer: { '@type': 'Answer', text: a },
    })),
  }
}

export default function FAQ() {
  const [openIdx, setOpenIdx] = useState<number | null>(null)

  useEffect(() => {
    const el = document.querySelector('script[data-schema="faq"]')
    if (el) {
      el.textContent = JSON.stringify(buildFaqSchema(), null, 2)
    }
  }, [])

  const toggle = (idx: number) => setOpenIdx(prev => (prev === idx ? null : idx))

  return (
    <section
      id="faq"
      className="py-20 lg:py-32 bg-white dark:bg-zinc-950"
      aria-labelledby="faq-heading"
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Heading */}
        <div className="text-center mb-12">
          <h2
            id="faq-heading"
            className="mb-4"
            style={{
              fontFamily: 'var(--font-display)',
              fontWeight: 600,
              fontSize: '1.9375rem',
              color: 'var(--color-text-dark)',
              lineHeight: 1.2,
            }}
          >
            Частые вопросы
          </h2>
          <p
            style={{
              fontFamily: 'var(--font-ui)',
              fontSize: '1rem',
              color: 'var(--color-text-secondary)',
              lineHeight: 1.6,
            }}
          >
            Ответы на самые распространённые вопросы о платформе.
          </p>
        </div>

        {/* Accordion */}
        <div
          className="border divide-y dark:border-zinc-800"
          style={{
            borderRadius: 'var(--radius-sm)',
            borderColor: 'var(--color-border)',
          }}
        >
          {FAQ_ITEMS.map(({ q, a }, idx) => {
            const isOpen = openIdx === idx
            return (
              <div key={idx}>
                <button
                  onClick={() => toggle(idx)}
                  aria-expanded={isOpen}
                  className="w-full flex items-center justify-between gap-4 px-5 py-4 text-left transition-colors hover:bg-black/[0.02] dark:hover:bg-white/[0.03] min-h-[48px]"
                  style={{ fontFamily: 'var(--font-ui)' }}
                >
                  <span
                    className="font-medium text-sm"
                    style={{ color: 'var(--color-text-dark)' }}
                  >
                    {q}
                  </span>
                  <motion.span
                    animate={{ rotate: isOpen ? 180 : 0 }}
                    transition={{ duration: 0.2 }}
                    className="shrink-0"
                  >
                    <ChevronDown
                      size={18}
                      style={{ color: 'var(--color-text-muted)' }}
                      aria-hidden="true"
                    />
                  </motion.span>
                </button>

                <AnimatePresence initial={false}>
                  {isOpen && (
                    <motion.div
                      key="content"
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: 'auto', opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.22, ease: 'easeInOut' }}
                      style={{ overflow: 'hidden' }}
                    >
                      <p
                        className="px-5 pb-5 text-sm"
                        style={{
                          fontFamily: 'var(--font-ui)',
                          color: 'var(--color-text-secondary)',
                          lineHeight: 1.65,
                        }}
                      >
                        {a}
                      </p>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            )
          })}
        </div>

        {/* Bottom CTA */}
        <p
          className="mt-10 text-center text-sm"
          style={{ fontFamily: 'var(--font-ui)', color: 'var(--color-text-muted)' }}
        >
          Остались вопросы?{' '}
          <a
            href={BOT_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="font-medium underline underline-offset-4 transition-opacity hover:opacity-70"
            style={{ color: 'var(--color-brand-blue)' }}
          >
            Напишите нам в Telegram-бот
          </a>
        </p>
      </div>
    </section>
  )
}
