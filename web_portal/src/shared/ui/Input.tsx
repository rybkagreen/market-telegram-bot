interface InputProps {
  label?: string
  placeholder?: string
  value: string
  onChange: (value: string) => void
  type?: 'text' | 'email' | 'password' | 'number' | 'time' | 'date'
  error?: string
  hint?: string
  invalid?: boolean
  className?: string
  disabled?: boolean
  min?: number | string
  max?: number | string
}

export function Input({
  label,
  placeholder,
  value,
  onChange,
  type = 'text',
  error,
  hint,
  invalid = false,
  className = '',
  disabled = false,
  min,
  max,
}: InputProps) {
  const hasError = !!error || invalid

  return (
    <div className={`flex flex-col gap-1.5 ${className}`}>
      {label && (
        <label className="text-sm font-medium text-text-secondary">{label}</label>
      )}
      <input
        type={type}
        value={value}
        placeholder={placeholder}
        min={min}
        max={max}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        className={`
          px-3 py-2 rounded-md border bg-harbor-elevated text-text-primary
          placeholder:text-text-tertiary
          focus:outline-none focus:ring-2 focus:border-transparent
          disabled:opacity-50 disabled:pointer-events-none
          transition-all duration-fast
          ${hasError
            ? 'border-danger focus:ring-danger'
            : 'border-border-active focus:ring-accent'
          }
        `}
      />
      {error && <p className="text-xs text-danger" role="alert">{error}</p>}
      {hint && !error && <p className="text-xs text-text-tertiary">{hint}</p>}
    </div>
  )
}
