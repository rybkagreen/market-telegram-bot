# S-47 Phase 6 — design-from-tokens redesign (§7.17)

**Branch:** `feat/s-47-ui-redesign-ds-v2`
**Commits:** `8ed3b37` → `2f46fda` (7 commits)
**Plan reference:** `reports/20260419_diagnostics/FIX_PLAN_07_ui_redesign_ds_v2.md` §7.17

## Scope

Phase 6 covers the ~30 screens that had **no handoff mockup** and were designed
by extending DS v2 tokens (§7.1) and primitives (§7.4) via the patterns from
§§7.5–7.12 and the handoff-pixel screens (§7.5a). Work was split into four
logical groups committed separately.

## Affected screens by group

### Group A — Advertiser (14 screens)
- `web_portal/src/screens/advertiser/MyCampaigns.tsx` — ScreenHeader + 4
  SummaryTiles + pill filter bar + Card-grouped row list, per-row Icon-based
  actions, sort buttons using `sort/sort-asc/sort-desc` sprite. Emoji filter
  pills replaced with DS v2 filter pills.
- `web_portal/src/screens/advertiser/campaign/_shell.tsx` **(new)** —
  `CampaignWizardShell` (ScreenHeader + StepIndicator 1..6 + sticky footer).
- `web_portal/src/screens/advertiser/campaign/CampaignCategory.tsx` — uses
  shell, removes legacy StepIndicator dup.
- `web_portal/src/screens/advertiser/campaign/CampaignChannels.tsx` — shell
  footer shows running total; sticky footer replaces custom bottom bar.
- `web_portal/src/screens/advertiser/campaign/CampaignFormat.tsx` — shell +
  FormatSelector unchanged; back/next in footer.
- `web_portal/src/screens/advertiser/campaign/CampaignText.tsx` — shell + Tabs
  AI / manual + AI-variant cards with numbered glyphs + char counter surfaced
  in footer.
- `web_portal/src/screens/advertiser/campaign/CampaignArbitration.tsx` — shell
  + per-channel ArbRows (icon-prefixed) + FeeBreakdown + error notification.
  Empty-selected-channels state gets a themed dropzone.
- `web_portal/src/screens/advertiser/campaign/CampaignWaiting.tsx` — rebuilt
  as a post-creation **status screen** (not wizard): ScreenHeader + 2-column
  layout (Timeline + details side-panel). No StepIndicator.
- `web_portal/src/screens/advertiser/campaign/CampaignPublished.tsx` — ditto,
  status screen; uses `FeeBreakdown` for the 85/15 split and side panel
  with action buttons (stats / ORD / dispute).
- `web_portal/src/screens/advertiser/CampaignPayment.tsx` — 2-column layout:
  gradient hero with total, counter-offer diff panel (was/became), FeeBreakdown
  card, action panel on right. Emoji notifications replaced.
- `web_portal/src/screens/advertiser/CampaignCounterOffer.tsx` — split-card
  (owner vs your counter) with live Δ indicator + Textarea comment.
- `web_portal/src/screens/advertiser/CampaignVideo.tsx` — ScreenHeader +
  FileUpload card + preview card with use-video toggle + sticky footer.
- `web_portal/src/screens/advertiser/OrdStatus.tsx` — wired to `useOrdStatus`
  /`useRegisterOrd` (was stub), Timeline of 4 ОРД stages + details panel +
  retry button on failure.
- `web_portal/src/screens/advertiser/AdvertiserFrameworkContract.tsx` —
  AcceptRules-like layout: text pane + side panel with comment/checkbox/CTA.
- `web_portal/src/screens/advertiser/AdvAnalytics.tsx` — 4 SummaryTiles + chart
  card + top-channels table with tone-coloured CTR.

### Group B — Owner (10 screens)
- `web_portal/src/screens/owner/OwnChannels.tsx` — SummaryTiles + pill filter
  + sort buttons + responsive channel-card grid with StatCells; compare bar &
  modal rebuilt with DS v2 classes. The legacy table+MobileCard duplication
  was removed.
- `web_portal/src/screens/owner/OwnChannelDetail.tsx` — hero-card with StatTiles
  + 2 ActionTiles + danger/restore section. Inline SVGs removed; uses sprite
  Icons (`settings`, `requests`).
- `web_portal/src/screens/owner/OwnAddChannel.tsx` — ScreenHeader + 3 cards
  (input+check, info, category grid) + admin test-mode toggle.
- `web_portal/src/screens/owner/OwnChannelSettings.tsx` — SectionCards (price,
  formats toggle rows, schedule inputs, auto-accept). Legacy Cards dropped.
- `web_portal/src/screens/owner/OwnRequests.tsx` — SummaryTiles including
  pending earnings potential + pill filter + sort + unified Row list (no
  table/MobileCard split).
- `web_portal/src/screens/owner/OwnRequestDetail.tsx` — 2-column layout with
  Timeline + text + counter/reject forms on left, FeeBreakdown + actions +
  published-result card on right.
- `web_portal/src/screens/owner/OwnPayouts.tsx` — gradient hero with cooldown
  countdown + 3 SummaryTiles + history list using DS v2 row pattern.
- `web_portal/src/screens/owner/OwnPayoutRequest.tsx` — 2-column with preset
  amounts, running FeeBreakdown in right column.
- `web_portal/src/screens/owner/OwnAnalytics.tsx` — 4 KPI SummaryTiles + two
  chart cards + by-channel table (charts unchanged).
- `web_portal/src/screens/owner/DisputeResponse.tsx` — 2-column with
  advertiser comment + owner-response Textarea left, placement details right.

### Group C — Shared disputes + common (6 screens)
- `web_portal/src/screens/shared/MyDisputes.tsx` — pill filter + grouped row
  list, tone-coloured status icons.
- `web_portal/src/screens/shared/OpenDispute.tsx` — 2-column with reason-grid +
  description left, placement details + evidence panel right. Uses Icon
  `delete`/`blocked`/`chat` for reasons.
- `web_portal/src/screens/shared/DisputeDetail.tsx` — 2-column with
  reason/comments/resolution left, Timeline of dispute lifecycle right.
- `web_portal/src/screens/common/LegalProfilePrompt.tsx` — Hero with gradient
  top-stripe + 3 benefits + primary/ghost CTAs.
- `web_portal/src/screens/common/LegalProfileView.tsx` — 2-column field-row
  sections + verification badges (`verified`/`passport` icons).
- `web_portal/src/screens/common/ContractDetail.tsx` — Hero with type/status
  + sign/download action bar + KepWarning retained.

### Group D — Admin (11 screens + shared TaxSummaryBase)
- `web_portal/src/screens/admin/AdminDashboard.tsx` — 4 KpiTiles + finance
  section (3 FinTiles + FeeBreakdown) + QuickAction sidebar.
- `web_portal/src/screens/admin/AdminUsersList.tsx` — search bar + pill
  filter + bulk-action toolbar with Select + responsive table with
  tone-coloured plan badges.
- `web_portal/src/screens/admin/AdminUserDetail.tsx` — hero-card with
  StatTiles + 3 SectionCards (top-up / platform credit / gamification bonus)
  with AdminInput primitives.
- `web_portal/src/screens/admin/AdminDisputesList.tsx` — pill filter +
  icon-prefixed list rows with visual action-button span (whole row clickable).
- `web_portal/src/screens/admin/AdminDisputeDetail.tsx` — status banner +
  split advertiser/owner panels + 2×2 tone-coloured resolution grid + slider
  for `partial`.
- `web_portal/src/screens/admin/AdminFeedbackList.tsx` — pill filter + card
  list with status pill and chevron.
- `web_portal/src/screens/admin/AdminFeedbackDetail.tsx` — 2-column with
  message + response form + status-change side panel.
- `web_portal/src/screens/admin/AdminPayouts.tsx` — pill filter + card rows
  with StatCells (gross/fee/net) + inline rejection form.
- `web_portal/src/screens/admin/AdminAccounting.tsx` — thin wrapper (subtitle
  + crumbs props); rendering now handled by rewritten TaxSummaryBase.
- `web_portal/src/screens/admin/AdminTaxSummary.tsx` — ditto; KUDiR table
  rewritten with DS v2 table styling.
- `web_portal/src/screens/admin/AdminPlatformSettings.tsx` — 2-column
  SectionCards for legal data and payment requisites + single save CTA.
- `web_portal/src/components/admin/TaxSummaryBase.tsx` — rebuilt to use
  ScreenHeader (new `subtitle`/`crumbs` props) + KpiCells + DS v2 action
  buttons; formatRub helper retained.

## Primitives touched

- `Button` (`web_portal/src/shared/ui/Button.tsx`) — unchanged contract; phase 6
  surfaces `iconLeft`/`iconRight` across every screen to eliminate emoji labels.
- `_shell.tsx` in `screens/advertiser/campaign/` — local wizard primitive,
  not exported via `@shared/ui`.

No new `@shared/ui` primitives were added — phase 6 composed existing ones.

## Business logic / contract impact

**None.** Phase 6 is purely a visual/UX redesign. All query keys, mutation
payloads, navigation routes, FSM transitions, and API endpoints are unchanged.
The wizard navigation order (`/adv/campaigns/new/category → channels → format
→ text → terms`) and status-screen paths (`waiting`/`payment`/`published`) are
preserved.

One micro-behaviour change: `AdminDisputesList` rows became fully-clickable —
the former "Решить" button inside the row was a child-button nested in a
click-through wrapper. It now renders as a visual span; the whole row is a
button that navigates to `/disputes/:id`.

## DB / API / FSM

No changes.

## Lint / type-check

- `npx tsc --noEmit` — 0 errors after all 7 commits.
- `npx eslint src/screens/ src/components/admin/` — 0 errors on changed files
  after fixing `_shell.tsx` constant re-export. The pre-existing
  `BalanceHero.tsx` React Compiler warning (Phase 4) is unchanged.
- `docker compose up -d --build nginx api` — succeeds; `nginx` container is
  running.

## Commits

| Phase | Commit | Subject |
|-------|--------|---------|
| 6.1 | `8ed3b37` | redesign MyCampaigns per DS v2 |
| 6.2 | `34b250a` | unify campaign wizard per DS v2 |
| 6.3 | `8eb9875` | redesign 6 advertiser standalones per DS v2 |
| 6.4 | `c678afd` | redesign 10 owner screens per DS v2 |
| 6.5 | `e0ff6dc` | redesign disputes + legal common screens per DS v2 |
| 6.6 | `3195aa9` | redesign 11 admin screens per DS v2 |
| fix | `2f46fda` | AdminDisputesList row-action + _shell lint |

## Next steps

- Phase 7 — a11y pass (§7.18), performance pass (§7.19).
- Do **not** merge into `develop` until all of §7.18–7.21 ship and visual
  review is complete per plan §7.0 instructions.

🔍 Verified against: 2f46fda5e6b4fae9938513be6824ffd0df913a70 | 📅 Updated: 2026-04-20T00:00:00Z
