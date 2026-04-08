interface CheckboxProps {
  checked: boolean
  onChange: (checked: boolean) => void
  label?: string
  disabled?: boolean
  className?: string
}

export function Checkbox({ checked, onChange, label, disabled, className = '' }: CheckboxProps) {
  return (
    <label className={`flex items-center gap-2 cursor-pointer ${disabled ? 'opacity-50 pointer-events-none' : ''} ${className}`}>
      <div
        role="checkbox"
        aria-checked={checked}
        tabIndex={0}
        onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') onChange(!checked) }}
        className={`w-5 h-5 rounded border flex items-center justify-center transition-all duration-fast shrink-0 ${
          checked
            ? 'bg-accent border-accent text-accent-text'
            : 'border-border-active bg-harbor-elevated'
        }`}
        onClick={() => onChange(!checked)}
      >
        {checked && (
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
          </svg>
        )}
      </div>
      {label && <span className="text-sm text-text-secondary">{label}</span>}
    </label>
  )
}
