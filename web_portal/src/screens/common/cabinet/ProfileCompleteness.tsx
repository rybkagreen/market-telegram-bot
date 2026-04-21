import { useMe } from '@/hooks/queries'
import { useMyLegalProfile } from '@/hooks/useLegalProfileQueries'
import { useContracts } from '@/hooks/queries'
import { Icon } from '@shared/ui'

interface Step {
  label: string
  done: boolean
}

export function ProfileCompleteness() {
  const { data: user } = useMe()
  const { data: legal } = useMyLegalProfile()
  const { data: contracts } = useContracts('advertiser_framework')

  const contractSigned = Boolean(
    contracts?.items?.some((c) => c.contract_status === 'signed'),
  )

  const steps: Step[] = [
    { label: 'Telegram привязан', done: Boolean(user?.telegram_id) },
    { label: 'Имя заполнено', done: Boolean(user?.first_name?.trim()) },
    { label: 'Юридический профиль', done: Boolean(legal?.is_complete) },
    { label: 'Правила приняты', done: Boolean(user?.platform_rules_accepted_at) },
    { label: 'Оферт-договор', done: contractSigned },
  ]
  const done = steps.filter((s) => s.done).length
  const pct = Math.round((done / steps.length) * 100)
  const R = 26
  const C = 2 * Math.PI * R

  return (
    <section className="rounded-xl bg-harbor-card border border-border p-5">
      <header className="mb-4">
        <h3 className="font-display text-[14px] font-semibold text-text-primary">Профиль</h3>
        <p className="text-[11px] text-text-tertiary mt-0.5">
          {done} из {steps.length} шагов завершено
        </p>
      </header>

      <div className="flex items-center gap-4 mb-4">
        <div className="relative w-16 h-16 flex-shrink-0">
          <svg width="64" height="64" style={{ transform: 'rotate(-90deg)' }} aria-hidden="true">
            <circle cx="32" cy="32" r={R} fill="none" stroke="var(--color-harbor-secondary)" strokeWidth="5" />
            <circle
              cx="32"
              cy="32"
              r={R}
              fill="none"
              stroke="var(--color-accent)"
              strokeWidth="5"
              strokeLinecap="round"
              strokeDasharray={`${(C * pct) / 100} ${C}`}
              style={{ transition: 'stroke-dasharray 0.6s ease' }}
            />
          </svg>
          <div className="absolute inset-0 grid place-items-center font-display text-base font-bold text-text-primary tabular-nums">
            {pct}%
          </div>
        </div>
        <div className="flex-1 text-[13px] text-text-primary leading-snug">
          {pct === 100
            ? 'Профиль полностью готов — выплаты доступны.'
            : 'Завершите настройку, чтобы открыть все функции.'}
        </div>
      </div>

      <ul className="flex flex-col gap-2">
        {steps.map((s, i) => (
          <li key={i} className="flex items-center gap-2 text-[12.5px]">
            <span
              className={`w-4 h-4 rounded-full grid place-items-center flex-shrink-0 ${
                s.done ? 'bg-success text-harbor-bg' : 'border-[1.5px] border-dashed border-border-active'
              }`}
            >
              {s.done && <Icon name="check" size={10} strokeWidth={2.5} />}
            </span>
            <span
              className={s.done ? 'text-text-tertiary line-through decoration-text-tertiary' : 'text-text-primary'}
            >
              {s.label}
            </span>
          </li>
        ))}
      </ul>
    </section>
  )
}
