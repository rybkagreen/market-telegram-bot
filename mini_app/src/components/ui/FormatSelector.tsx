import { useHaptic } from '@/hooks/useHaptic'
import styles from './FormatSelector.module.css'

interface Format {
  id: string
  label: string
  description?: string
  icon?: string
  price?: string
}

interface FormatSelectorProps {
  formats: Format[]
  selected?: string
  onSelect: (id: string) => void
}

export function FormatSelector({ formats, selected, onSelect }: FormatSelectorProps) {
  const haptic = useHaptic()

  const handleSelect = (id: string) => {
    haptic.select()
    onSelect(id)
  }

  return (
    <div className={styles.list}>
      {formats.map((fmt) => {
        const isActive = selected === fmt.id
        return (
          <button
            key={fmt.id}
            type="button"
            className={`${styles.item} ${isActive ? styles.active : ''}`}
            onClick={() => handleSelect(fmt.id)}
          >
            <span className={styles.radio}>{isActive ? '◉' : '○'}</span>
            {fmt.icon && <span className={styles.icon}>{fmt.icon}</span>}
            <span className={styles.content}>
              <span className={styles.label}>{fmt.label}</span>
              {fmt.description && <span className={styles.description}>{fmt.description}</span>}
            </span>
            {fmt.price && <span className={styles.price}>{fmt.price}</span>}
          </button>
        )
      })}
    </div>
  )
}
