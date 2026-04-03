/**
 * Text — typography component using --rh-* design tokens
 *
 * Props:
 *   variant   — size: xs | sm | md | lg | xl
 *   weight    — normal | medium | semibold | bold
 *   color     — primary | secondary | muted | accent | danger | success | warning | inverse
 *   font      — body (default) | display | mono
 *   leading   — normal (default) | tight | relaxed
 *   align     — left (default) | center | right
 *   truncate  — enable single-line truncation
 *   tabular   — enable tabular-nums for mono-aligned numbers
 *   as        — HTML element: span | p | h1 | h2 | h3 | label | div
 *   className — additional CSS classes
 *   children  — text content
 */

import { createElement, type ReactNode } from 'react'
import styles from './Text.module.css'

export type TextVariant = 'xs' | 'sm' | 'md' | 'lg' | 'xl'
export type TextWeight = 'normal' | 'medium' | 'semibold' | 'bold'
export type TextColor = 'primary' | 'secondary' | 'muted' | 'accent' | 'danger' | 'success' | 'warning' | 'inverse'
export type TextFont = 'body' | 'display' | 'mono'
export type TextLeading = 'normal' | 'tight' | 'relaxed'
export type TextAlign = 'left' | 'center' | 'right'
export type TextAs = 'span' | 'p' | 'h1' | 'h2' | 'h3' | 'label' | 'div'

interface TextProps {
  variant?: TextVariant
  weight?: TextWeight
  color?: TextColor
  font?: TextFont
  leading?: TextLeading
  align?: TextAlign
  truncate?: boolean
  tabular?: boolean
  as?: TextAs
  className?: string
  children: ReactNode
}

const TAG_MAP: Record<TextAs, string> = {
  span: 'span',
  p: 'p',
  h1: 'h1',
  h2: 'h2',
  h3: 'h3',
  label: 'label',
  div: 'div',
}

export function Text({
  variant = 'md',
  weight = 'normal',
  color = 'primary',
  font = 'body',
  leading = 'normal',
  align = 'left',
  truncate = false,
  tabular = false,
  as = 'span',
  className,
  children,
}: TextProps) {
  const Tag = TAG_MAP[as]

  const cn = [
    styles.text,
    styles[variant],
    styles[weight],
    styles[color],
    styles[font],
    leading !== 'normal' ? styles[leading] : '',
    align !== 'left' ? styles[align] : '',
    truncate ? styles.truncate : '',
    tabular ? styles.tabular : '',
    className ?? '',
  ].filter(Boolean).join(' ')

  return createElement(Tag, { className: cn }, children)
}
