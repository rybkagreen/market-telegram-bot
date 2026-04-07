interface SelectProps {
  value: string
  onChange: (value: string) => void
  options: { value: string; label: string }[]
  placeholder?: string
  className?: string
  disabled?: boolean
}

export function Select({ value, onChange, options, placeholder = 'Выберите...', className = '', disabled }: SelectProps) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      disabled={disabled}
      className={`w-full px-4 py-2.5 bg-harbor-elevated border border-border rounded-md text-text-primary text-sm
        focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent/30
        disabled:opacity-50 disabled:pointer-events-none transition-all duration-fast ${className}`}
    >
      <option value="" disabled>{placeholder}</option>
      {options.map((opt) => (
        <option key={opt.value} value={opt.value}>
          {opt.label}
        </option>
      ))}
    </select>
  )
}
