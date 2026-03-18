import { motion } from 'motion/react'
import { useHaptic } from '@/hooks/useHaptic'
import styles from './Toggle.module.css'

interface ToggleProps {
  checked: boolean
  onChange: (checked: boolean) => void
  disabled?: boolean
  label?: string
}

export function Toggle({ checked, onChange, disabled = false, label }: ToggleProps) {
  const haptic = useHaptic()

  const handleClick = () => {
    if (disabled) return
    haptic.select()
    onChange(!checked)
  }

  return (
    <label className={`${styles.wrapper} ${disabled ? styles.disabled : ''}`}>
      {label && <span className={styles.label}>{label}</span>}
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        disabled={disabled}
        className={`${styles.track} ${checked ? styles.on : ''}`}
        onClick={handleClick}
      >
        <motion.span
          className={styles.thumb}
          layout
          transition={{ type: 'spring', stiffness: 500, damping: 35 }}
        />
      </button>
    </label>
  )
}
