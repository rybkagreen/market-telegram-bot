# CHANGES — Sidebar Icon-Only Collapsed State

**Date:** 2026-04-10
**Sprint:** S-29 (Sidebar UX Improvements)
**Type:** feat(mini-app)

---

## Summary

The web_portal sidebar (`PortalShell`) previously had a binary open/closed state. When closed, the entire sidebar disappeared including navigation icons. This change introduces a **3-state sidebar** (`open` → `collapsed` → `closed`) so that on desktop, closing the full sidebar leaves a 64px icon rail with all navigation tool icons visible and clickable.

---

## Files Changed

| File | Lines changed | Description |
|------|--------------|-------------|
| `web_portal/src/stores/portalUiStore.ts` | ~36 lines (rewritten) | Replaced `sidebarOpen: boolean` with `sidebarMode: 'open' \| 'collapsed' \| 'closed'`. Added `openSidebar()`, `collapseSidebar()`, `closeSidebar()`, `toggleSidebar(isDesktop)`. Default: `'collapsed'` on desktop. |
| `web_portal/src/components/layout/PortalShell.tsx` | ~284 lines (rewritten JSX) | 3-state conditional rendering: width classes, icon centering, label hide/show via `isCollapsed` boolean, `title` tooltips on collapsed nav buttons, user footer compact mode, header button icon swap (Menu ↔ X). |

---

## Behavior Matrix

| State | Width | Labels | Logo text | User info | Mobile? |
|-------|-------|--------|-----------|-----------|---------|
| `open` | 240px | visible | visible | full | overlay |
| `collapsed` | 64px | hidden (tooltip) | hidden (anchor only) | avatar + logout | N/A |
| `closed` | 0px | — | — | — | default |

### Desktop toggle cycle
`open` → click ✕ → `collapsed` (icon rail) → click ☰ → `open`

### Mobile toggle cycle
`closed` → click ☰ → `open` (overlay) → click ✕/backdrop → `closed`

---

## Breaking Changes

**None.** The store API changed (`sidebarOpen` → `sidebarMode`), but `PortalShell.tsx` is the only consumer and was updated in the same commit. No other component reads `usePortalUiStore`.

---

## CSS / Visual Changes

- Sidebar width transitions: `w-60` ↔ `w-16` ↔ `w-0` via `transition-all duration-300`
- Collapsed nav buttons: `justify-center px-2 py-3` (centered icons, no text padding)
- Collapsed user footer: `justify-center gap-2`, name/username hidden, avatar + logout visible
- Collapsed logo: `justify-center px-2`, "RekHarbor" text hidden, anchor emoji visible

---

## Build Verification

- `tsc --noEmit` — 0 errors
- `vite build` — ✓ built in ~720ms, 0 warnings

---

## Related

- No API changes
- No DB changes
- No backend changes

🔍 Verified against: `$(git rev-parse HEAD)` | 📅 Updated: 2026-04-10T12:00:00Z
