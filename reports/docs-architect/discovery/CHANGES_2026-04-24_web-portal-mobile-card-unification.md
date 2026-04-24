# CHANGES 2026-04-24 — Cabinet account card + list-card unification

## Context

User feedback after the jitter-fix round:
1. Cabinet mobile — "карточка telegram" (account info block) rendered
   disjointed: avatar alone, three label/value stacked fields with
   tiny uppercase labels, and the "Выйти" button on its own row —
   read as three unrelated pieces.
2. Across Каналы (`OwnChannels`), Кампании (`MyCampaigns`), Размещения
   (`OwnRequests`) — mobile card layouts were visually inconsistent
   ("разная, хаотичная"). Three screens, three different card shapes.

## Changes

### `web_portal/src/screens/common/Cabinet.tsx` — account card rewrite

Before: `flex flex-col sm:flex-row` with four children stacked on
mobile (avatar / 3-row grid of uppercase labels / logout button).

After:
- Always `flex items-center gap-3` on mobile — avatar + identity +
  logout inline.
- Identity column on mobile: big name + a single meta row
  (`@handle · telegram_id`) — drops the three separate uppercase
  labels that cluttered the vertical flow.
- Identity column on desktop (`sm+`): preserved as 3-col grid with
  uppercase labels (Имя / Username / Telegram ID).
- Logout on mobile: icon-only `44×44` button (`title` / `aria-label`
  keep the "Выйти" semantics). Logout on desktop: icon + text button.

Result: account card reads as a single horizontal unit on mobile
(avatar | name + meta | logout icon), matching the visual density of
the rest of the screen.

### Unified list card layout — `MyCampaigns` / `OwnRequests` / `OwnChannels`

All three screens now share the same mobile card skeleton:

```
[status-avatar] title + id + optional-meta
                subtitle (ad text / channel title)
                date ←→ price  (justify-between)

                           [action] [action]
```

Row container: `flex flex-col gap-3 sm:flex-row sm:items-center`.
Desktop (`sm+`) retains the row-with-cells layout via `sm:contents`
on the identity wrapper, so status-pill and price cells participate
in the outer flex.

Per-screen tweaks applied:

- `advertiser/MyCampaigns.tsx` — campaign row rewrapped in
  `flex flex-col sm:flex-row` stack (was a single tight flex-row that
  squeezed icon + content + 2 action buttons into 343px). Actions
  now on their own row on mobile, justified right. Status text pill
  preserved only on desktop; mobile relies on the avatar colour +
  aria-label. `aria-label` on all icon buttons.
- `owner/OwnRequests.tsx` — same unified pattern (already had a
  partial stack from the previous session; polished to match
  MyCampaigns).
- `owner/OwnChannels.tsx` — category chip/button moved into the
  header row on mobile (was a dedicated "Col 3" that added an
  otherwise-empty row). On `@3xl` (desktop container width) the
  dedicated column stays. The category picker (when editing) is
  rendered as a full-width row below the header only on mobile —
  no layout change on desktop. Net effect: mobile OwnChannels card
  goes from 4 visual sections (identity / stats / category / actions)
  to 3 (identity-with-category / stats / actions), matching the
  density of MyCampaigns and OwnRequests.

## Business / API impact

Zero. Pure UI restructuring.

## Verification

- `tsc --noEmit` — exit 0.
- `vite build` — 709ms, no bundle size regression.
- `docker compose build --no-cache nginx` + `up -d --force-recreate
  nginx` — container `(healthy)` serving fresh dist.

## Files touched

- `web_portal/src/screens/common/Cabinet.tsx`
- `web_portal/src/screens/advertiser/MyCampaigns.tsx`
- `web_portal/src/screens/owner/OwnChannels.tsx`
- (`web_portal/src/screens/owner/OwnRequests.tsx` already aligned in
  previous session; left untouched this round.)

🔍 Verified against: 2b5375f9178ee18ac233a01acac4ca8748fd95f5 | 📅 Updated: 2026-04-24T00:00:00Z
