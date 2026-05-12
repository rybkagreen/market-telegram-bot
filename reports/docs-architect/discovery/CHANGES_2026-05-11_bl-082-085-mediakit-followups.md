# 2026-05-11 — BL-082..085: mediakit-followups latent issues (BACKLOG entries)

## What

Adds 4 new BACKLOG entries (BL-082 through BL-085) surfaced by PROMPT_23
web_portal/ probe (2026-05-11) during B.4 mediakit download button planning.
None of these are blocking; all are latent DX / type-drift / observability
concerns suitable for future cleanup batches.

## Entries added

- **BL-082** — `User` type 3 sources of truth (`authStore.ts` / `lib/types.ts`
  / `lib/types/user.ts`). Type drift risk. Resolution: consolidate to single
  canonical, deprecate copies. Effort small.
- **BL-083** — TanStack Query devtools в devDependencies но не mounted в
  `App.tsx`. DX-only. Effort trivial (~5 lines).
- **BL-084** — `authStore` без `persist` middleware — manual localStorage
  sync, no cross-tab `storage` event listener. Edge-case cross-tab logout
  inconsistency. Effort small.
- **BL-085** — Sentry `afterResponse` auto-captures every non-ok response →
  noise на known 4xx (404/403 на download endpoints, 401 already handled by
  redirect). Effort small.

## Files

- `reports/docs-architect/BACKLOG.md` (append 4 entries between BL-081 and
  `## Closed items` section)
- `reports/docs-architect/discovery/CHANGES_2026-05-11_bl-082-085-mediakit-followups.md`
  (this file)

## Verification

Backend baseline preserved bit-for-bit (no Python touched):

- `make format-check`: 0
- `make lint`: 7 (BL-024)
- `make typecheck`: 0
- `make ci-local`: 0F / 1008P / 2S / 0E, exit 1

Frontend: untouched (`web_portal/` baseline pre-existing 2 err + 6 warn known,
no edits here).

## Phase B progress

- B.1 + B.2 + B.3 + B.4 ✅ merged
- B.5 (mini app preview card) ⏸ pending — fresh session recommended
- B.6 (docs sweep + ship) ⏸ pending — CHANGELOG [Unreleased] + BACKLOG
  closeouts для B.1-B.5 + BL-076 T1.2-D1 + BL-078

## Notes

Source probe: PROMPT_23 (`tmp/web_portal_probe.md` produced 2026-05-11).
Marina-approved batch as docs-only addition.

🔍 Verified against: feature/chore-bl-mediakit-followups HEAD (post-commit SHA in git log) | 📅 Updated: 2026-05-11
