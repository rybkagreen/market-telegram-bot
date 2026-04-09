# CHANGES — Dark Mode for Landing Page

🔍 Verified against: `HEAD` | 📅 Updated: `2026-04-09T00:00:00Z`

## Summary

Implemented full dark mode for the RekHarbor landing page using Tailwind CSS v4 `@custom-variant dark` class strategy with `ThemeProvider` React context and `localStorage` persistence.

## Approach

- **Tailwind v4 dark mode**: `@custom-variant dark (&:where(.dark, .dark *))` in `index.css`
- **Theme toggle**: `ThemeProvider` wraps `<App>`, adds/removes `.dark` class on `<html>`, persists to `localStorage('rekharbor-theme')`
- **CSS variable overrides**: `.dark` selector overrides all `--color-*`, `--shadow-*` CSS custom properties — components using `var(--color-*)` automatically adapt
- **Tailwind dark: utilities**: Hardcoded colors (`text-gray-900`, `bg-white`, etc.) get explicit `dark:` counterparts (`dark:text-zinc-100`, `dark:bg-zinc-950`)

## Dark Color Palette

| Token | Light | Dark |
|-------|-------|------|
| `--color-bg-primary` | `#ffffff` | `#0f0f11` |
| `--color-bg-light` | `#f0f0f0` | `#1a1a1f` |
| `--color-bg-dark` | `#181e25` | `#09090b` |
| `--color-text-primary` | `#222222` | `#e4e4e7` |
| `--color-text-dark` | `#18181b` | `#f4f4f5` |
| `--color-text-secondary` | `#45515e` | `#a1a1aa` |
| `--color-text-muted` | `#767676` | `#71717a` |
| `--color-border` | `#e5e7eb` | `#27272a` |
| `--shadow-card` | `rgba(0,0,0,0.08)` | `rgba(0,0,0,0.3)` |

## Files Changed

| File | Change |
|------|--------|
| `landing/src/index.css` | Added `@custom-variant dark` + `.dark {}` CSS variable overrides |
| `landing/src/context/ThemeContext.tsx` | **NEW** — ThemeProvider + useTheme hook + localStorage persistence |
| `landing/src/App.tsx` | Wrapped in `<ThemeProvider>` |
| `landing/src/components/Header.tsx` | Dark mode toggle button (Sun/Moon), dark variants for nav, logo, mobile drawer |
| `landing/src/components/Hero.tsx` | Dark variants: bg, gradient, badge, heading, subtitle, CTAs, stat cards |
| `landing/src/components/Features.tsx` | Dark variants: section bg, card bg/border, subtitle CSS var |
| `landing/src/components/HowItWorks.tsx` | Dark variants: tab pill, subtitle CSS var, CTA button |
| `landing/src/components/Tariffs.tsx` | Dark variants: section bg, card bg/border, CTA button text |
| `landing/src/components/Compliance.tsx` | Dark variants: gradient end uses CSS var, card bg/border, subtitle CSS var |
| `landing/src/components/FAQ.tsx` | Dark variants: section bg, accordion border, hover bg |
| `landing/src/components/Footer.tsx` | Dark variant: bg-zinc-950 (slightly darker than gray-900) |

## Verification

- ✅ `npm run build` — 0 errors (CSS 30.04 kB → +4 kB from dark variants)
- ✅ `npx eslint src/` — 0 errors
- ✅ `npx tsc --noEmit` — 0 errors

## Impact

- **Visual**: Full dark mode available via toggle in header
- **Persistence**: User preference saved to `localStorage`
- **No breaking changes** — light mode is default
- **No API/FSM/DB contract changes**
- **Accessibility**: Toggle button has `aria-label` describing current action
