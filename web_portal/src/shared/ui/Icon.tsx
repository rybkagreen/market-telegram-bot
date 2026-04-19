import type { CSSProperties } from 'react'
import { FILLED_AVAILABLE, type IconName } from './icon-names'

declare global {
  interface Window {
    __RH_ICON_SPRITE?: string
  }
}

interface IconProps {
  name: IconName
  size?: number
  variant?: 'outline' | 'fill'
  className?: string
  strokeWidth?: number
  style?: CSSProperties
  title?: string
}

function getSpriteUrl() {
  if (typeof window === 'undefined') return '/icons/rh-sprite.svg'
  const override = window.__RH_ICON_SPRITE
  if (override === undefined) return '/icons/rh-sprite.svg'
  return override
}

export function Icon({
  name,
  size = 20,
  variant = 'outline',
  className = '',
  strokeWidth,
  style,
  title,
}: IconProps) {
  const useFill = variant === 'fill' && FILLED_AVAILABLE.has(name)
  const symbolId = useFill ? `rh-${name}-fill` : `rh-${name}`
  const spriteUrl = getSpriteUrl()

  const strokeStyle = strokeWidth != null
    ? ({ ['--rh-stroke-w' as string]: String(strokeWidth) } as CSSProperties)
    : undefined

  const svgStyle: CSSProperties = {
    display: 'inline-block',
    verticalAlign: 'middle',
    flexShrink: 0,
    ...strokeStyle,
    ...style,
  }

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 20 20"
      fill="none"
      aria-hidden={title ? undefined : true}
      role={title ? 'img' : undefined}
      className={`rh-icon rh-icon-${name} ${className}`.trim()}
      style={svgStyle}
    >
      {title && <title>{title}</title>}
      <use href={`${spriteUrl}#${symbolId}`} />
    </svg>
  )
}
