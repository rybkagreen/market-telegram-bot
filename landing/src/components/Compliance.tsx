import { ShieldCheck, Lock, Banknote, Star } from 'lucide-react'
import { CANCEL_REFUND_ADVERTISER, PAYOUT_FEE, formatRatePct } from '../lib/constants'

const BLOCKS = [
  {
    icon: ShieldCheck,
    title: 'Регистрация в ОРД и erid-маркировка',
    text:
      'Каждое размещение автоматически регистрируется в Яндекс ОРД (Оператор Рекламных Данных, API v7) через 6-шаговый протокол. Публикуемый пост получает erid-токен согласно требованиям ФЗ «О рекламе». Вам не нужно вникать в детали — платформа делает это за вас.',
  },
  {
    icon: Lock,
    title: 'Защита персональных данных (152-ФЗ)',
    text:
      'Персональные данные пользователей защищены согласно 152-ФЗ. Конфиденциальные поля (ИНН, паспортные данные, контакты) хранятся в зашифрованном виде. Передача данных третьим лицам — только Яндекс ОРД (обязательно по закону) и YooKassa (платёжный оператор).',
  },
  {
    icon: Banknote,
    title: 'Эскроу и возвраты',
    text:
      `После оплаты средства блокируются на платформе и не поступают владельцу канала до подтверждения публикации (ESCROW-001). Возврат: 100% до начала публикации, ${formatRatePct(CANCEL_REFUND_ADVERTISER, 0)} после — согласно правилам платформы. Выплаты через YooKassa, комиссия за вывод ${formatRatePct(PAYOUT_FEE)}.`,
  },
  {
    icon: Star,
    title: 'Репутация и доверие',
    text:
      'Система репутации (0.0–10.0, стартовый рейтинг 5.0) автоматически фиксирует нарушения: срыв сроков, необоснованные отказы, несоответствие содержания. 30 дней без нарушений восстанавливают рейтинг. При критически низком уровне — временная блокировка аккаунта.',
  },
] as const

export default function Compliance() {
  return (
    <section
      id="compliance"
      className="py-20 lg:py-32"
      style={{
        background: 'linear-gradient(180deg, var(--color-bg-light) 0%, var(--color-bg-primary) 100%)',
      }}
      aria-labelledby="compliance-heading"
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Heading */}
        <div className="max-w-2xl mx-auto text-center mb-14">
          <h2
            id="compliance-heading"
            className="mb-4"
            style={{
              fontFamily: 'var(--font-display)',
              fontWeight: 600,
              fontSize: '1.9375rem',
              color: 'var(--color-text-dark)',
              lineHeight: 1.2,
            }}
          >
            Соответствие требованиям
          </h2>
          <p
            style={{
              fontFamily: 'var(--font-ui)',
              fontSize: '1rem',
              color: 'var(--color-text-secondary)',
              lineHeight: 1.6,
            }}
          >
            Платформа разработана с учётом действующего российского законодательства
            в сфере рекламы и персональных данных.
          </p>
        </div>

        {/* 2×2 grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 max-w-4xl mx-auto">
          {BLOCKS.map(({ icon: Icon, title, text }) => (
            <div
              key={title}
              className="flex flex-col gap-4 p-7 border"
              style={{
                borderRadius: 'var(--radius-md)',
                borderColor: 'var(--color-border)',
                background: 'var(--color-bg-primary)',
                boxShadow: 'var(--shadow-card)',
              }}
            >
              <div
                className="inline-flex items-center justify-center w-11 h-11 shrink-0"
                style={{
                  background: 'rgba(20,86,240,0.08)',
                  borderRadius: 'var(--radius-sm)',
                }}
              >
                <Icon size={22} style={{ color: 'var(--color-brand-blue)' }} aria-hidden="true" />
              </div>
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
              <p
                style={{
                  fontFamily: 'var(--font-ui)',
                  fontSize: '0.875rem',
                  color: 'var(--color-text-secondary)',
                  lineHeight: 1.65,
                }}
              >
                {text}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
