# S-47 — UI Redesign DS v2 (progress)

Feature branch: `feat/s-47-ui-redesign-ds-v2` (from main `5d7451d`).
Source of truth: `reports/20260419_diagnostics/FIX_PLAN_07_ui_redesign_ds_v2.md`.

## Phase 1 — Foundation (tokens, fonts, icon sprite) — completed 2026-04-20

### globals.css (§7.1)
- **Verified:** existing `web_portal/src/styles/globals.css` already mirrors handoff
  `project/globals.css` verbatim (@theme tokens, light-mode `@layer theme`, base-layer
  rules, custom utilities). No rewrite needed.
- **Added:** `.rh-icon .rh-stroke` and `.rh-icon .rh-fill` component-layer rules so
  the 132-symbol sprite renders correctly.
- **Added:** `@keyframes ui-spin` and `@keyframes ui-skeleton` (ported from handoff
  `ui.jsx` runtime-inject, now static CSS — so primitives can reference them without
  a JS side-effect).

### Fonts (§7.2.1)
- **Verified:** Google Fonts `Outfit` / `DM Sans` / `JetBrains Mono` already wired in
  `web_portal/index.html` (`preconnect` + `css2?family=…`). No change needed.

### Icon system (§7.2.2)
- **Added:** `web_portal/public/icons/rh-sprite.svg` — direct copy of handoff
  `icons/icons.svg` (132 symbols in 10 groups, 20×20, stroke 1.5, rounded joins,
  24 fill variants for nav states).
- **Added:** `web_portal/src/shared/ui/icon-names.ts` — `ICON_NAMES` literal-union
  const + `IconName` type + `FILLED_AVAILABLE` set. Mirrors handoff `Icons.jsx`.
- **Added:** `web_portal/src/shared/ui/Icon.tsx` — TSX port of handoff `<Icon>`.
  Props: `name: IconName`, `variant: outline|fill`, `size=20`, `strokeWidth?`,
  `className?`, `title?`. Uses `<use href="/icons/rh-sprite.svg#rh-{name}">` with
  `window.__RH_ICON_SPRITE` override hook for post-inline-injection path rewriting.
- **Added:** `web_portal/src/shared/ui/IconSpriteLoader.tsx` — fetches sprite once,
  inlines into `<body>` under `#__rh-icon-sprite`, sets `__RH_ICON_SPRITE=""` so
  subsequent `<use>` refs resolve locally.
- **Mounted:** `IconSpriteLoader` inside `PortalShell.tsx` return root (once per
  session), so all shell + screen icons share a single inline-sprite copy.
- **Exported** `Icon`, `IconSpriteLoader`, `IconName`, `ICON_NAMES`, `FILLED_AVAILABLE`
  from `@shared/ui/index.ts`.

### Files touched
- `web_portal/src/styles/globals.css` — +20 lines (icon rules + 2 keyframes)
- `web_portal/public/icons/rh-sprite.svg` — new (37 KB)
- `web_portal/src/shared/ui/icon-names.ts` — new (43 lines)
- `web_portal/src/shared/ui/Icon.tsx` — new (63 lines)
- `web_portal/src/shared/ui/IconSpriteLoader.tsx` — new (33 lines)
- `web_portal/src/shared/ui/index.ts` — +4 exports
- `web_portal/src/components/layout/PortalShell.tsx` — mount IconSpriteLoader

### Verification
- `cd web_portal && npx tsc --noEmit -p tsconfig.app.json` → 0 errors.

### Deferred
- `LUCIDE_MAPPING.md` — will be authored when migration of existing `lucide-react`
  imports begins (Phase 8). The full table is already in `FIX_PLAN_07 §7.23` so the
  standalone file is a duplicate until it starts serving as the migration checklist.
- ESLint `no-restricted-imports` rule for `lucide-react` — added with other Phase 8
  polish to avoid churning the lint config before any call-site is migrated.
- Dev-only icon gallery route `/dev/icons` — backlog.

---

🔍 Verified against: feat/s-47-ui-redesign-ds-v2 (post `5d7451d`) | 📅 Updated: 2026-04-20T02:30:00Z
