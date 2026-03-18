import { useHaptic } from '@/hooks/useHaptic'
import styles from './AmountChips.module.css'

interface AmountChipsProps {
  amounts: number[]
  selected?: number
  onSelect: (amount: number) => void
  formatter?: (amount: number) => string
}

export function AmountChips({
  amounts,
  selected,
  onSelect,
  formatter = (n) => `${n.toLocaleString('ru-RU')} ₽`,
}: AmountChipsProps) {
  const haptic = useHaptic()

  const handleSelect = (amount: number) => {
    haptic.select()
    onSelect(amount)
  }

  return (
    <div className={styles.row}>
      {amounts.map((amount) => (
        <button
          key={amount}
          type="button"
          className={`${styles.chip} ${selected === amount ? styles.active : ''}`}
          onClick={() => handleSelect(amount)}
        >
          {formatter(amount)}
        </button>
      ))}
    </div>
  )
}
