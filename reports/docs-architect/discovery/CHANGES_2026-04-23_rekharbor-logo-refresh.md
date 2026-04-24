# CHANGES 2026-04-23 — RekHarbor Logo Refresh

Replaces the placeholder anchor/emoji/RH-badge logos across all
frontends with the new brand-grade RekHarbor logo (custom icon +
wordmark). Supports OS-level theme via `prefers-color-scheme`.

## Affected files

### Brand assets (new)

- **New** `web_portal/public/brand/rekharbor_full_light.svg` —
  icon + wordmark, `#14A5A8` teal + `#0F2540` navy. For light UI.
- **New** `web_portal/public/brand/rekharbor_full_dark.svg` —
  derived from `_light.svg` with `Harbor` text recoloured
  `#E5ECF2` (light neutral) so it remains legible on the
  default dark portal background.
- **New** `web_portal/public/brand/rekharbor_icon_teal.svg` —
  monochrome teal icon for the collapsed sidebar on dark theme.
- **New** `web_portal/public/brand/rekharbor_icon_dark.svg` —
  monochrome navy icon for the collapsed sidebar on light theme.

### Frontend components

- **Modified** `web_portal/src/components/layout/Sidebar.tsx`:
  replaced the gradient-box + `<Icon name="anchor">` + literal
  `RekHarbor` span with a `<picture>` element that swaps
  full/icon SVG based on `isCollapsed`, and swaps the
  light/dark variant via `<source media="(prefers-color-scheme: light)">`.
- **Modified** `web_portal/src/screens/auth/LoginPage.tsx`:
  removed the `⚓` emoji + `<h1>RekHarbor</h1>` duo, replaced
  with theme-aware full-logo `<picture>`.

### Favicons

- **Replaced** `web_portal/public/favicon.svg` (previously
  missing — `index.html` referenced a 404). Now teal icon.
- **Replaced** `mini_app/public/favicon.svg` (was gradient
  rect with `⚓` emoji). Now teal icon.
- **Replaced** `landing/public/favicon.svg` (was `RH` text
  badge on `#1456f0`). Now teal icon.

### Landing social preview

- **Rewritten** `landing/public/assets/og-cover.svg` (1200×630).
  Replaces the Tailwind-blue `RekHarbor` badge with the new
  full logo (inline icon paths + DM Sans/Outfit wordmark) on a
  white→teal-tint gradient. Copy refreshed to reference the new
  brand accent `#14A5A8`.
- **Modified** `landing/scripts/generate-og.ts` — this is the
  real source of truth for `og-cover.svg` (ran by `npm run
  prebuild` inside the landing Docker build stage; it would
  otherwise stomp the hand-edited SVG). Template now emits the
  refreshed layout.

## Business-logic impact

None. Purely visual. No API, DB, FSM, or Celery task changes.

## Public contracts

No contract changes. No new endpoints, no Pydantic schema
changes — nothing to regenerate in `tests/unit/snapshots/*.json`.

## Theme behaviour

The portal resolves theme via `@media (prefers-color-scheme)`
(see `web_portal/src/styles/globals.css` line 59). The new
markup uses native `<picture><source media=…>` so no JS and no
extra CSS is required — the browser picks the correct file at
load time and re-evaluates on OS theme change.

## Residual notes

- Landing `src/components/Header.tsx` still uses a pure-text
  `<span>Rek</span><span>Harbor</span>` with Tailwind
  `text-blue-600` (not the brand `#14A5A8`). Not touched because
  the original request scoped to "logos with anchor"; this has
  no anchor. Recolour-or-replace deferred for a separate pass.
- `web_portal/public/icons/rh-sprite.svg` still contains an
  `anchor` symbol. It is now unused by the sidebar but kept in
  the sprite for any future decorative nautical-theme usage.

## Follow-up fixes (same day)

### Palette alignment

Initial commit used the placeholder teal `#14A5A8` from the sampled
JPG. Portal's `--color-accent` is `oklch(0.70 0.16 230)` = `#00AEEE`
(sky-cyan, not greenish-teal). All brand SVGs + `generate-og.ts`
retargeted:

| Role | Before | After |
|---|---|---|
| Icon / accent / `Rek` wordmark | `#14A5A8` | `#00AEEE` |
| `Harbor` on light theme | `#0F2540` | `#0C121A` (portal text-primary light) |
| `Harbor` on dark theme | `#E5ECF2` | `#E1E5EB` (portal text-primary dark) |

Applied via `sed` across all 7 brand SVG files + `generate-og.ts`
+ `og-cover.svg`.

### Sidebar logo swap (React remount)

The initial ternary rendered two `<picture>` elements with the same
tag and no `key`. React reconciliation reused the DOM `<img>`,
changing only `src` and `width/height` attrs. While the new SVG
loaded over the network, the browser displayed the **old** full
logo squished into the **new** 32×32 attrs — looking visually like
the full logo "shrinking" instead of a clean swap to the icon
variant. Fixed by:

- Adding `key="logo-full"` / `key="logo-icon"` to force a fresh
  mount on mode change.
- Pinning explicit pixel width on the expanded variant
  (`w-[158px]` matches the natural aspect at h=32) so Tailwind
  preflight's `max-width: 100%` cannot squash it during the
  300ms `aside` width transition.
- `shrink-0` on the `<img>` belt-and-braces against the parent
  flex container.

Same `width`/`height` hardening applied to `LoginPage.tsx`
(`w-[237px] h-12`).

🔍 Verified against: fix/plan-05-typed-exceptions (post follow-up) | 📅 Updated: 2026-04-23T23:05:00Z
