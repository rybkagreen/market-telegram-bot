# CHANGES — 2026-04-23 — Web-portal layout polish (OwnChannels / LegalProfile / Sidebar / Cabinet)

## Summary

Four related UX / alignment fixes on the web-portal:

1. Owner «Мои каналы» (`/own/channels`) — a single channel card
   rendered at ≈320px while the filter bar above it spanned the full
   content column. Multiple channels got squeezed into columns, which
   contradicts the intended «list of channels» UX.
2. Common «Юридический профиль» (`/legal-profile/view`) — when the
   user has no bank details (typical for individuals / self-employed),
   the `lg:grid-cols-2` container left the right half empty and
   rendered «Основные данные» at half width, misaligned with the
   full-width header and action buttons below.
3. Sidebar — nav icons were shifted right relative to the logo
   (logo `px-4` vs. nav `px-2.5` + button `px-2.5` = 20px); the user
   footer (avatar + handle + logout) visually conflicted in the
   collapsed width.
4. Sidebar — user footer removed; `Кабинет` moved to the bottom of
   the navigation; profile info (name / @handle / Telegram ID) and
   logout relocated to the Cabinet screen.

## Affected files

- `web_portal/src/screens/owner/OwnChannels.tsx`
  - Replaced `grid auto-fit minmax(320px, 1fr)` with a vertical stack
    (`flex flex-col gap-3.5`) so each card spans 100% of the content
    width regardless of item count.
  - Promoted each card to a container-query root (`@container`) and
    switched the internal layout to horizontal at `@3xl` (≥768px card
    width): header (avatar + @username + title) | 3 stat cells |
    category/«Выбрать категорию» block on the same row, action buttons
    (Сравнить / Настройки / Скрыть-Восстановить) below.
  - Narrow widths (mini-app, mobile viewport, sidebar-expanded desktop)
    still render the original vertical stack.

- `web_portal/src/screens/common/LegalProfileView.tsx`
  - Conditional grid: `lg:grid-cols-2` applied only when bank details
    exist (`profile.bank_name || profile.bank_account`). Otherwise the
    grid stays single-column at every breakpoint, and «Основные
    данные» fills the full content width.

- `web_portal/src/screens/owner/OwnChannels.tsx` — second pass
  - Replaced the vertical stack of cards with a single rounded
    container whose rows are separated by `border-t`, rendering as a
    responsive 4-column table (≥768px card width):
    `[channel info | 3 stats (280px) | category (160–200px) |
    actions (auto)]`. Columns align vertically across rows because
    widths are fixed.
  - Action column reduced to three equal-size icon buttons
    (`size="sm" icon`): compare / settings / hide|restore. The
    compare state is shown via `variant` (primary when in compare,
    secondary otherwise); the button no longer stretches.
  - «Без категории» hint collapsed into a single compact
    `Выбрать категорию` text button in the category column with a
    tooltip explaining the visibility impact.
  - At narrow widths (mini-app / mobile) the grid collapses to one
    column, so each cell stacks within the same table row.

- `web_portal/src/components/layout/Sidebar.tsx`
  - Nav container padding reduced from `px-2.5` to `px-2` and button
    inner padding from `px-2.5` to `px-2` (when expanded) — total
    8 + 8 = 16px, matching the logo's `px-4`. Icons now align
    vertically with the logo.
  - Active-item indicator `left-[-10px]` → `left-[-8px]` to stay
    flush with the new padding.
  - Removed the user footer (avatar + name/handle + logout icon)
    entirely.
  - `Кабинет` menu item moved from the first (top) section to a new
    last section (below `Администрирование` for admins).

- `web_portal/src/screens/common/Cabinet.tsx`
  - Added an Account card above the Balance hero: gradient avatar
    initial, three labelled fields (Имя / Username / Telegram ID)
    and a `Выйти` secondary button that calls `useAuthStore.logout`.
  - Uses existing `useMe` payload (`telegram_id`, `username`,
    `first_name`) — no backend change.

- `web_portal/src/components/layout/Topbar.tsx`
  - Replaced the sidebar toggle icon `more-h` / `close` with
    directional double-chevrons: `chevrons-left` when the sidebar is
    open (indicating «collapse»), `chevrons-right` when collapsed or
    closed (indicating «expand»).
  - Button upgraded to a 32×32 rounded control with a subtle
    `hover:bg-harbor-secondary` fill — matches the Notion/Linear/VS
    Code sidebar-toggle pattern.

## Business logic impact

None. Pure presentational change. No hooks, api modules, services,
routes, DB models, Celery tasks, FSM states, or permissions were
touched.

## Public contracts

- API: no change.
- FSM: no change.
- DB: no change.
- Web-portal ↔ backend contract: no change.

## Verification

- `docker compose up -d --build nginx api` — nginx/api rebuilt and
  recreated, containers healthy.
- Manual: reload `/own/channels` with `Ctrl+Shift+R`, confirm card
  width matches the filter panel at 1, 2, 3+ channels.

## Follow-ups

None.

---

🔍 Verified against: 2b5375f9178ee18ac233a01acac4ca8748fd95f5 | 📅 Updated: 2026-04-23T22:58:00+03:00
