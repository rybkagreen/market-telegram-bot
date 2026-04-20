# CHANGES — S-47 UI Redesign DS v2 — Mobile fixes (post-Phase 7)

**Sprint:** S-47 (UI redesign DS v2)
**Scope:** Hotfix applied between Phase 7 completion and Phase 8 merge, after
a mobile-browser visual review surfaced two production-blocking issues in
https://portal.rekharbor.ru/:

1. Icons were not rendering at all on iOS Safari / mobile Chrome.
2. Breadcrumbs in the topbar looked broken (missing separators, fell back to
   «Главная» on every detail page).

Both defects share a common root cause for the first and independent root
causes for the second — so they are fixed together but as two logically
distinct commits.

---

## 1. Icons — inline SVG sprite at build time

### Root cause

The portal rendered icons via `<svg><use href="/icons/rh-sprite.svg#rh-foo" /></svg>`
— an **external-file `<use>` reference**. This is a well-known incompatibility:
- iOS Safari (all versions through 17) does not resolve external `<use href>`
  for SVG sprites reliably; many mobile Chromium builds fail intermittently
  on HTTPS + cache-warmed external references.
- `IconSpriteLoader.tsx` tried to mitigate by fetching the sprite and
  injecting it into the DOM, then flipping `window.__RH_ICON_SPRITE = ''`
  so that later-mounted `<Icon>`s would use a local fragment `#rh-foo`.
  But the flag was not reactive — already-mounted `<Icon>` instances
  continued to reference the external URL, leaving icons blank on mobile.

### Fix

Inline the sprite directly into `index.html` at build time via a small Vite
`transformIndexHtml` plugin (`web_portal/vite-plugins/inline-sprite.ts`).
The sprite is now present in the DOM before React mounts, so every `<Icon>`
can safely use a local fragment reference that works in every browser
including the oldest iOS Safari.

This follows the same production pattern used by GitHub (Octicons),
Stripe, and Vercel — the sprite is a ~37 KB static asset that gzips to
~8 KB; adding it to the single-page HTML is well within budget and
eliminates the FOUC / race-condition surface entirely.

### Files

- `web_portal/vite-plugins/inline-sprite.ts` — **new**. Vite plugin that reads
  `public/icons/rh-sprite.svg`, strips the XML declaration, injects the
  `<svg>` immediately after the `<body>` open tag. `configureServer` wires
  dev-mode full-reload when the sprite file changes.
- `web_portal/vite.config.ts` — registers the plugin.
- `web_portal/src/shared/ui/Icon.tsx` — simplified: removed `getSpriteUrl()`,
  removed the `window.__RH_ICON_SPRITE` global, always renders
  `<use href="#rh-foo">`.
- `web_portal/src/shared/ui/IconSpriteLoader.tsx` — **deleted**. No longer
  needed; kept no backward-compat shim per project convention.
- `web_portal/src/shared/ui/index.ts` — removed the `IconSpriteLoader` export.
- `web_portal/src/components/layout/PortalShell.tsx` — removed the `<IconSpriteLoader />`
  mount and its import.

### Verification

```
curl -sk https://portal.rekharbor.ru/ | wc -c   # → 38565 (was ~1.2 KB)
curl -sk https://portal.rekharbor.ru/ | grep '<symbol id="rh-'   # → many matches
```

### Not changed

- The sprite file (`public/icons/rh-sprite.svg`) itself is untouched; it is
  still served at `/icons/rh-sprite.svg` as a regular public asset (in case
  external tools, e.g. design-system docs, want to consume it).
- Icon API surface — every existing `<Icon name="…" variant="…" size="…" />`
  call continues to work unchanged. No screen required edits.

---

## 2. Breadcrumbs — dynamic routes + mobile overflow

### Root cause

`Topbar.tsx` resolved crumbs by exact-match lookup in a `BREADCRUMB_MAP`
keyed by `location.pathname`. Detail screens with numeric route params
(`/own/channels/42`, `/adv/campaigns/7/payment`, `/admin/users/123`, …)
miss the lookup entirely and fall back to the single-item `['Главная']`,
so every detail page rendered a misleading one-crumb chain.

Additionally, on narrow viewports the nav had no overflow guard: a long
chain like «Реклама › Новая кампания › Категория» would push the bell
icon off-screen. And because the chevron separator is itself an `<Icon>`,
the icon-sprite bug above made the chain look like concatenated plain text.

### Fix

- **Normalise** `location.pathname` before lookup: collapse every numeric
  segment (`/\d+`) to `/:id`, producing the canonical route pattern used by
  react-router.
- **Extend `BREADCRUMB_MAP`** with entries for every dynamic route in
  `App.tsx`: owner channel/request/dispute detail screens, advertiser
  campaign-lifecycle screens (waiting / payment / counter-offer /
  published / dispute / ord), contract detail, shared dispute detail,
  admin user / dispute / feedback detail, framework contract, video
  creative, and `/dev/icons`.
- **Mobile-first overflow:** nav becomes `min-w-0 flex-1 md:flex-initial
  overflow-hidden`. For chains of 3+ crumbs, the middle crumbs get
  `hidden md:flex` — on mobile the user sees `First › Last`, on `md+`
  the full chain. Each crumb span gets `truncate` so even a single long
  crumb is clipped with an ellipsis instead of breaking layout. The
  obsolete `flex-1 md:hidden` spacer was removed — the nav's `flex-1`
  now takes that role.

### Files

- `web_portal/src/components/layout/Topbar.tsx` — normalisation, extended
  map, mobile-overflow classes.

### Not changed

- Route definitions in `App.tsx` — untouched. The breadcrumb chain is still
  driven by a flat map, not by react-router `handle` pattern (deferred;
  the map is sufficient and keeps the diff small).
- `portalUiStore.ts` — the unused `setBreadcrumbs` / `breadcrumbs` slice
  remains for future per-screen override use cases; no regressions.
- Crumbs are still non-interactive plain text (not `<a>` links); a future
  ticket may make intermediate crumbs clickable, but that is out of scope
  for this hotfix.

---

## Quality gates

- `npx tsc --noEmit` → exit 0 (web_portal).
- `docker compose up -d --build nginx` → rebuild + redeploy successful.
- `curl -sk -o /dev/null -w "%{http_code}" https://portal.rekharbor.ru/`
  → 200.
- Inlined sprite verified in served HTML (≈38 KB index.html, `<symbol
  id="rh-…">` tags present before `<div id="root">`).
- Mobile visual verification — requested from user after deploy.

---

🔍 Verified against: `e303a9b` (feat/s-47-ui-redesign-ds-v2 HEAD before fix) |
📅 Updated: 2026-04-20
