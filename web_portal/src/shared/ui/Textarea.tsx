interface TextareaProps {
  value: string
  onChange: (value: string) => void
  placeholder?: string
  rows?: number
  maxLength?: number
  className?: string
  disabled?: boolean
}

export function Textarea({ value, onChange, placeholder, rows = 3, maxLength, className = '', disabled }: TextareaProps) {
  return (
    <textarea
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      rows={rows}
      maxLength={maxLength}
      disabled={disabled}
      className={`w-full px-4 py-2.5 bg-harbor-elevated border border-border rounded-md text-text-primary text-sm
        placeholder:text-text-tertiary
        focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent/30
        disabled:opacity-50 disabled:pointer-events-none transition-all duration-fast resize-none ${className}`}
    />
  )
}
