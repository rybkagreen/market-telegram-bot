import { useHaptic } from '@/hooks/useHaptic'
import styles from './CategoryGrid.module.css'

interface Category {
  id: string
  label: string
  icon: string
}

interface CategoryGridProps {
  categories: Category[]
  selected?: string[]
  onToggle: (id: string) => void
  multi?: boolean
}

export function CategoryGrid({
  categories,
  selected = [],
  onToggle,
  multi = false,
}: CategoryGridProps) {
  const haptic = useHaptic()

  const handleToggle = (id: string) => {
    haptic.select()
    onToggle(id)
  }

  return (
    <div className={styles.grid}>
      {categories.map((cat) => {
        const isActive = selected.includes(cat.id)
        return (
          <button
            key={cat.id}
            type="button"
            className={`${styles.item} ${isActive ? styles.active : ''}`}
            onClick={() => handleToggle(cat.id)}
            aria-pressed={isActive}
          >
            <span className={styles.icon}>{cat.icon}</span>
            <span className={styles.label}>{cat.label}</span>
            {multi && isActive && <span className={styles.check}>✓</span>}
          </button>
        )
      })}
    </div>
  )
}
