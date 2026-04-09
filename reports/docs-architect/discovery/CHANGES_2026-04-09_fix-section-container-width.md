# CHANGES — Fix Section Container Width Consistency

🔍 Verified against: `HEAD` | 📅 Updated: `2026-04-09T00:00:00Z`

## Summary

Unified the outer container class across all landing section components to `max-w-7xl mx-auto px-4 sm:px-6 lg:px-8`.

## Root Cause

FAQ.tsx used `max-w-3xl` (48rem) while all other sections used `max-w-7xl` (80rem), causing visual inconsistency in page width.

Additionally, a prior fix removed a `*, *::before, *::after { margin: 0; padding: 0 }` CSS reset from `index.css` that was overriding Tailwind utility classes (`mx-auto`, `px-*`, etc.).

## Files Changed

| File | Change |
|------|--------|
| `landing/src/components/FAQ.tsx` | `max-w-3xl` → `max-w-7xl` on outer container div (line 75) |
| `landing/src/index.css` | Removed redundant `* { margin: 0; padding: 0 }` reset (already in Tailwind `@layer base`) |

## Components Audited (no changes needed)

| Component | Container Class |
|-----------|----------------|
| `Features.tsx` | `max-w-7xl mx-auto px-4 sm:px-6 lg:px-8` ✅ |
| `HowItWorks.tsx` | `max-w-7xl mx-auto px-4 sm:px-6 lg:px-8` ✅ |
| `Tariffs.tsx` | `max-w-7xl mx-auto px-4 sm:px-6 lg:px-8` ✅ |
| `Compliance.tsx` | `max-w-7xl mx-auto px-4 sm:px-6 lg:px-8` ✅ |

## Verification

- ✅ `npm run build` — 0 errors
- ✅ `npx eslint src/` — 0 errors
- ✅ `npx tsc --noEmit` — 0 errors

## Impact

- **Visual:** All landing sections now have identical max-width (80rem) and horizontal padding
- **No breaking changes**
- **No API/FSM/DB contract changes**
