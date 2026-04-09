import { useState } from 'react'
import { AnimatePresence, motion } from 'motion/react'
import {
  PlusSquare,
  CreditCard,
  Radio,
  BarChart2,
  Plug,
  CheckSquare,
  Banknote,
  ArrowRight,
} from 'lucide-react'
import { BOT_URL } from '../lib/constants'

type TabKey = 'advertiser' | 'owner'

const TABS: { key: TabKey; label: string }[] = [
  { key: 'advertiser', label: 'Рекламодатель' },
  { key: 'owner', label: 'Владелец канала' },
]

const STEPS: Record<TabKey, { icon: typeof PlusSquare; title: string; description: string }[]> = {
  advertiser: [
    {
      icon: PlusSquare,
      title: 'Создай кампанию',
      description:
        'Выбери категорию, подходящие каналы и формат размещения. Загрузи рекламный текст или сгенерируй его с помощью AI за несколько секунд.',
    },
    {
      icon: CreditCard,
      title: 'Оплати и зафиксируй бронь',
      description:
        'Деньги уходят в эскроу — блокируются на платформе. Владелец канала получает уведомление о новой заявке и может принять или предложить другую цену (до 3 раундов).',
    },
    {
      icon: Radio,
      title: 'Автоматическая публикация',
      description:
        'Бот публикует пост в указанное время, следит за сроком размещения и проверяет наличие поста в канале. erid-маркировка добавляется автоматически.',
    },
    {
      icon: BarChart2,
      title: 'Аналитика и завершение',
      description:
        'После удаления поста эскроу разблокируется и владелец получает выплату. Вы видите отчёт о размещении и подтверждение регистрации в ОРД.',
    },
  ],
  owner: [
    {
      icon: Plug,
      title: 'Подключи канал',
      description:
        'Добавь бота @RekHarborBot как администратора канала. Настрой базовую цену, допустимые форматы размещения и расписание публикаций.',
    },
    {
      icon: CheckSquare,
      title: 'Принимай заявки',
      description:
        'Получай уведомления о новых запросах. Соглашайся на условия, предлагай свою цену или отклоняй — до 3 раундов переговоров с рекламодателем.',
    },
    {
      icon: Banknote,
      title: 'Получай выплаты',
      description:
        'После завершения размещения средства автоматически зачисляются на ваш баланс. Вывод через YooKassa. Комиссия платформы — 15%, вам — 85%.',
    },
  ],
}

export default function HowItWorks() {
  const [activeTab, setActiveTab] = useState<TabKey>('advertiser')

  return (
    <section
      id="how-it-works"
      className="py-20 lg:py-32"
      style={{ background: 'var(--color-bg-light)' }}
      aria-labelledby="how-heading"
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Heading */}
        <div className="max-w-2xl mx-auto text-center mb-10">
          <h2
            id="how-heading"
            className="mb-4"
            style={{
              fontFamily: 'var(--font-display)',
              fontWeight: 600,
              fontSize: '1.9375rem',
              color: 'var(--color-text-dark)',
              lineHeight: 1.2,
            }}
          >
            Как это работает
          </h2>
          <p
            style={{
              fontFamily: 'var(--font-ui)',
              fontSize: '1rem',
              color: 'var(--color-text-secondary)',
              lineHeight: 1.6,
            }}
          >
            Весь процесс — от заявки до выплаты — проходит внутри Telegram-бота.
          </p>
        </div>

        {/* Tab switcher */}
        <div className="flex justify-center mb-12">
          <div
            className="inline-flex p-1 gap-1"
            style={{
              background: 'var(--color-border)',
              borderRadius: '9999px',
            }}
            role="tablist"
            aria-label="Выберите роль"
          >
            {TABS.map(({ key, label }) => (
              <button
                key={key}
                role="tab"
                aria-selected={activeTab === key}
                onClick={() => setActiveTab(key)}
                className="relative px-5 py-2 text-sm font-medium transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2"
                style={{
                  fontFamily: 'var(--font-ui)',
                  borderRadius: '9999px',
                  color: activeTab === key ? 'var(--color-text-dark)' : 'var(--color-text-secondary)',
                  background: 'transparent',
                  zIndex: 1,
                }}
              >
                {activeTab === key && (
                  <motion.span
                    layoutId="tab-pill"
                    className="absolute inset-0 bg-white dark:bg-zinc-800"
                    style={{
                      borderRadius: '9999px',
                      boxShadow: 'var(--shadow-card)',
                    }}
                    transition={{ type: 'spring', stiffness: 400, damping: 35 }}
                  />
                )}
                <span className="relative z-10">{label}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Steps */}
        <AnimatePresence mode="wait">
          <motion.div
            key={activeTab}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -12 }}
            transition={{ duration: 0.22, ease: 'easeOut' }}
            className="max-w-2xl mx-auto"
            role="tabpanel"
          >
            <ol className="relative flex flex-col gap-0">
              {STEPS[activeTab].map(({ icon: Icon, title, description }, idx) => {
                const isLast = idx === STEPS[activeTab].length - 1
                return (
                  <li key={title} className="relative flex gap-5">
                    {/* Left column: number + line */}
                    <div className="flex flex-col items-center">
                      <div
                        className="flex items-center justify-center w-10 h-10 shrink-0 font-semibold text-sm text-white z-10"
                        style={{
                          background: 'var(--color-brand-blue)',
                          borderRadius: '50%',
                          fontFamily: 'var(--font-display)',
                        }}
                        aria-hidden="true"
                      >
                        {idx + 1}
                      </div>
                      {!isLast && (
                        <div
                          className="w-px flex-1 my-2"
                          style={{ background: 'var(--color-border)' }}
                          aria-hidden="true"
                        />
                      )}
                    </div>

                    {/* Content */}
                    <div className={`flex flex-col gap-1.5 pb-8 ${isLast ? '' : ''}`}>
                      <div className="flex items-center gap-2">
                        <Icon
                          size={16}
                          style={{ color: 'var(--color-brand-blue)' }}
                          aria-hidden="true"
                        />
                        <h3
                          className="font-semibold"
                          style={{
                            fontFamily: 'var(--font-display)',
                            fontSize: '1rem',
                            color: 'var(--color-text-dark)',
                          }}
                        >
                          {title}
                        </h3>
                      </div>
                      <p
                        style={{
                          fontFamily: 'var(--font-ui)',
                          fontSize: '0.875rem',
                          color: 'var(--color-text-secondary)',
                          lineHeight: 1.65,
                        }}
                      >
                        {description}
                      </p>
                    </div>
                  </li>
                )
              })}
            </ol>
          </motion.div>
        </AnimatePresence>

        {/* CTA */}
        <div className="flex justify-center mt-10">
          <a
            href={BOT_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 px-6 py-3 text-sm font-semibold text-white transition-opacity hover:opacity-90 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2"
            style={{
              fontFamily: 'var(--font-ui)',
              background: 'var(--color-brand-blue)',
              borderRadius: 'var(--radius-sm)',
            }}
          >
            Начать в Telegram
            <ArrowRight size={16} aria-hidden="true" />
          </a>
        </div>
      </div>
    </section>
  )
}
