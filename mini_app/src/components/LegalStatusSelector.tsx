import type { LegalStatus } from '@/lib/types'
import styles from './LegalStatusSelector.module.css'

interface Option {
  value: LegalStatus
  icon: string
  title: string
  desc: string
}

const OPTIONS: Option[] = [
  { value: 'legal_entity', icon: '🏢', title: 'Юридическое лицо', desc: 'ООО, АО и другие организации' },
  { value: 'individual_entrepreneur', icon: '👤', title: 'Индивидуальный предприниматель', desc: 'ИП с расчётным счётом' },
  { value: 'self_employed', icon: '📱', title: 'Самозанятый', desc: 'НПД, ЮMoney-кошелёк' },
  { value: 'individual', icon: '🙋', title: 'Физическое лицо', desc: 'Выплата на карту, НДФЛ удерживается' },
]

interface LegalStatusSelectorProps {
  value: LegalStatus | null
  onChange: (status: LegalStatus) => void
}

export function LegalStatusSelector({ value, onChange }: LegalStatusSelectorProps) {
  return (
    <div className={styles.list}>
      {OPTIONS.map((opt) => (
        <div
          key={opt.value}
          role="button"
          tabIndex={0}
          className={`${styles.option} ${value === opt.value ? styles.selected : ''}`}
          onClick={() => onChange(opt.value)}
          onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') onChange(opt.value) }}
        >
          <span className={styles.icon}>{opt.icon}</span>
          <div className={styles.text}>
            <p className={styles.title}>{opt.title}</p>
            <p className={styles.desc}>{opt.desc}</p>
          </div>
        </div>
      ))}
    </div>
  )
}
