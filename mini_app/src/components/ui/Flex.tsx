/**
 * Flex — layout primitive using --rh-* spacing tokens
 *
 * Props:
 *   direction  — row (default) | column | rowReverse | columnReverse
 *   gap        — 4px-grid index: 0–16 (maps to var(--rh-space-N))
 *   align      — start | end | center | baseline | stretch
 *   justify    — start | end | center | between | around | evenly
 *   wrap       — false (default) | true | reverse
 *   grow       — make flex: 1 1 0%
 *   className  — additional CSS classes
 *   style      — inline style overrides (rare)
 *   children   — flex items
 */

import type { CSSProperties, ReactNode } from 'react'
import styles from './Flex.module.css'

export type FlexDirection = 'row' | 'column' | 'rowReverse' | 'columnReverse'
export type FlexAlign = 'start' | 'end' | 'center' | 'baseline' | 'stretch'
export type FlexJustify = 'start' | 'end' | 'center' | 'between' | 'around' | 'evenly'
export type FlexWrap = false | true | 'reverse'

interface FlexProps {
  direction?: FlexDirection
  gap?: 0 | 1 | 2 | 3 | 4 | 5 | 6 | 8 | 10 | 12 | 16
  align?: FlexAlign
  justify?: FlexJustify
  wrap?: FlexWrap
  grow?: boolean
  className?: string
  style?: CSSProperties
  children: ReactNode
}

const SPACE_MAP: Record<number, string> = {
  0: 'var(--rh-space-0)',
  1: 'var(--rh-space-1)',
  2: 'var(--rh-space-2)',
  3: 'var(--rh-space-3)',
  4: 'var(--rh-space-4)',
  5: 'var(--rh-space-5)',
  6: 'var(--rh-space-6)',
  8: 'var(--rh-space-8)',
  10: 'var(--rh-space-10)',
  12: 'var(--rh-space-12)',
  16: 'var(--rh-space-16)',
}

export function Flex({
  direction = 'row',
  gap,
  align,
  justify,
  wrap = false,
  grow = false,
  className,
  style,
  children,
}: FlexProps) {
  const cn = [
    styles.flex,
    styles[direction],
    styles[`align${align?.charAt(0).toUpperCase()}${align?.slice(1)}`] ?? '',
    styles[`justify${justify?.charAt(0).toUpperCase()}${justify?.slice(1)}`] ?? '',
    wrap === true ? styles.wrap : wrap === 'reverse' ? styles.wrapReverse : styles.noWrap,
    grow ? styles.grow : '',
    className ?? '',
  ].filter(Boolean).join(' ')

  const gapStyle: CSSProperties | undefined = gap !== undefined
    ? { gap: SPACE_MAP[gap] }
    : undefined

  const mergedStyle = gapStyle || style
    ? { ...gapStyle, ...style }
    : undefined

  return (
    <div className={cn} style={mergedStyle}>
      {children}
    </div>
  )
}
