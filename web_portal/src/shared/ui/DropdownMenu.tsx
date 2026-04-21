import { useEffect, useRef, useState } from 'react'
import { Icon } from './Icon'
import type { IconName } from './icon-names'

export interface DropdownMenuItem {
  label: string
  icon?: IconName
  onClick?: () => void
  href?: string
  disabled?: boolean
  tone?: 'default' | 'danger'
}

interface DropdownMenuProps {
  trigger: React.ReactNode
  items: DropdownMenuItem[]
  align?: 'start' | 'end'
  className?: string
}

export function DropdownMenu({
  trigger,
  items,
  align = 'end',
  className = '',
}: DropdownMenuProps) {
  const [open, setOpen] = useState(false)
  const rootRef = useRef<HTMLDivElement>(null)
  const firstItemRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    if (!open) return
    const onDocClick = (e: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) setOpen(false)
    }
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false)
    }
    document.addEventListener('mousedown', onDocClick)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onDocClick)
      document.removeEventListener('keydown', onKey)
    }
  }, [open])

  useEffect(() => {
    if (open) firstItemRef.current?.focus()
  }, [open])

  const alignClass = align === 'end' ? 'right-0' : 'left-0'

  return (
    <div ref={rootRef} className={`relative inline-flex ${className}`}>
      <div onClick={() => setOpen((v) => !v)} className="inline-flex">
        {trigger}
      </div>
      {open && (
        <div
          role="menu"
          className={`absolute top-[calc(100%+6px)] ${alignClass} z-40 min-w-[180px] rounded-lg border border-border bg-harbor-card shadow-[0_8px_24px_oklch(0_0_0_/_0.25)] py-1.5`}
        >
          {items.map((item, i) => {
            const tone =
              item.tone === 'danger'
                ? 'text-danger hover:bg-danger-muted'
                : 'text-text-primary hover:bg-harbor-elevated'
            const baseCls = `w-full flex items-center gap-2 px-3 py-2 text-[13px] font-medium transition-colors text-left disabled:opacity-50 disabled:pointer-events-none ${tone}`
            const onSelect = () => {
              if (item.disabled) return
              item.onClick?.()
              setOpen(false)
            }
            if (item.href) {
              return (
                <a
                  key={i}
                  href={item.href}
                  role="menuitem"
                  className={baseCls}
                  onClick={() => setOpen(false)}
                >
                  {item.icon && <Icon name={item.icon} size={14} />}
                  <span className="flex-1">{item.label}</span>
                </a>
              )
            }
            return (
              <button
                key={i}
                ref={i === 0 ? firstItemRef : undefined}
                type="button"
                role="menuitem"
                disabled={item.disabled}
                onClick={onSelect}
                className={baseCls}
              >
                {item.icon && <Icon name={item.icon} size={14} />}
                <span className="flex-1">{item.label}</span>
              </button>
            )
          })}
        </div>
      )}
    </div>
  )
}
