# CHANGES — B.6.2 BACKLOG sweep + IMPLEMENTATION_PLAN overlay update

**Date:** 2026-05-11
**Branch:** `feature/b6-2-backlog-plan-overlay`
**Base:** `develop` @ `2b0d0ab`
**Author:** Claude Code (executor) / Marina (decision owner)

## Summary

Final Phase B docs closure. `BACKLOG.md`: 2 closeouts (BL-076 T1.2-D1
inline, BL-078 IN-PHASE-CLOSED) + 5 new entries (BL-086 logo resolver,
BL-087 theme_color tinting, BL-088 landing probe, BL-089 unused dep,
BL-090 stop-hook fires loop). `IMPLEMENTATION_PLAN_ACTIVE.md`: Phase B
overlay refresh reflecting B.1-B.6.1 done + B.6.2 closure stamp + Phase 8
placeholder updated + branch HEADs sync.

Docs-only commit, no functional code changes. Closes Phase B mediakit
workstream — feature implementation complete на develop, polish tracked
under explicit BL entries.

## BACKLOG updates

### Closeouts (2)

- **BL-076 T1.2-D1** — CLOSED 2026-05-11 inline within BL-076 (sub-entry
  level; other 18 T1.2-Dx sub-entries remain OPEN). Resolution: BL-078
  Phase B execution chose investigation path (a) compute-from-existing-fields;
  4 mypy errors eliminated; `test_get_mediakit_data` un-skipped. Closure
  annotation appended after Priority line, before T1.2-D2 sub-entry.
- **BL-078** — Status line updated к `IN-PHASE-CLOSED 2026-05-11 — Phase B
  implementation complete (B.1-B.6.2 closure batch). Residual polish
  tracked under BL-086 (logo resolver), BL-087 (theme_color tinting).
  Phase 8 may revisit для deeper feature work.` Body preserved (history
  retained per sub-block prohibition "preserve original entry content").

### New entries (5)

Appended at tail of `## Active items` section, before `## Closed items`
heading. All follow BL-085 canonical template (Status / Created / Source /
Statement / Closure trigger / Effort / Priority / Refs).

- **BL-086** — Mediakit logo resolver / Telegram file_id image proxy.
  Sources: PROMPT_28 B.5 mini_app preview screen CHANGES; PROMPT_24/25
  B.4 download path. Feature gap; 3 closure variants (proxy endpoint /
  pre-resolved signed URL / S3 mirror). Effort medium, priority low.
- **BL-087** — Mediakit theme_color tinting. Source: PROMPT_28 B.5
  CHANGES. UX polish; apply `theme_color` к mini_app preview screen
  elements (parity с web_portal PDF rendering). Effort small, priority
  low.
- **BL-088** — `landing/` frontend surface probe. Source: Phase B
  mediakit workstream identifying third frontend dir unprobed.
  Operational/observability gap; deep-dive probe candidate. Effort small,
  priority low.
- **BL-089** — `@telegram-apps/sdk-react` unused dep в `mini_app/`.
  Source: PROMPT_26 mini_app probe surprise #1 (referenced в B.5
  CHANGES). Dep hygiene; `npm uninstall` + verify build clean. Effort
  trivial, priority low.
- **BL-090** — Stop-hook fires loop on Phase A research-only outputs.
  Source: PROMPT_28 B.5 Phase A (~500+ fires), PROMPT_30 B.6.2 Phase A
  (~9 fires). L71 candidate pattern. UX noise (no functional impact); 3
  closure variants (server-side tune / repo hook config / accept +
  BL-016 silent-ignore current state). Effort small / negligible,
  priority low.

## IMPLEMENTATION_PLAN_ACTIVE.md overlay

Four edits на repo-root `IMPLEMENTATION_PLAN_ACTIVE.md`:

1. **L3 metadata** — Last updated date refreshed; `develop` hash updated
   к `2b0d0ab pre-B.6.2-merge` (honest snapshot at file-write time per
   `49813f0` precedent).
2. **L54 BL-078 Phase B row** — Status `🚧 IN FLIGHT` → `✅ DONE`. Merge
   count `4 feature merges` → `8 feature merges` (precleanup + B.1-B.6.1
   + B.6.2 = 8 marker hashes listed). Body extended к describe B.4
   (web_portal download button), B.5.1 (advertiser endpoint), B.5
   (mini_app preview), B.6.1 (CHANGELOG consolidation), B.6.2 (this
   closure).
3. **L59 Phase 8 placeholder row** — Removed "BL-078 (mediakit B.4+)"
   reference (now in-phase closed). Body updated к acknowledge in-phase
   closure date + polish BL pointers.
4. **L63 branch HEADs** — `develop @ 49813f0` → `develop @ 2b0d0ab`
   (post-B.6.1 merge).

Status overlay structure (table at L40-59) preserved — no new rows
added; existing row updates only.

## Files touched (this commit)

- `reports/docs-architect/BACKLOG.md` — `+179 / −1` (T1.2-D1 closure
  bullet + BL-078 Status line + 5 new entries appended).
- `IMPLEMENTATION_PLAN_ACTIVE.md` — `+4 / −4` (4 surgical line replacements).
- `reports/docs-architect/discovery/CHANGES_2026-05-11_b6-2-backlog-plan-overlay.md`
  (this file, new).

## Baselines (preserved bit-for-bit)

Identical к develop @ `2b0d0ab` (re-verified empirically at Шаг 1 of this
sub-block + Шаг 5 pre-commit gates):

| Gate | Baseline | This commit |
|------|----------|-------------|
| `make format-check` | 0/401 files | 0/401 files |
| `make lint` | 7 errors (BL-024) | 7 errors (BL-024) |
| `make typecheck` | 0 errors / 293 source files | 0 errors / 293 source files |
| `make ci-local` pytest | 0F / 1013P / 2S / 0E | 0F / 1013P / 2S / 0E |
| `make ci-local` exit | 1 (aggregator on lint) | 1 (aggregator on lint) |

Docs-only change cannot regress code gates by construction (touches only
`BACKLOG.md` + `IMPLEMENTATION_PLAN_ACTIVE.md` + new `CHANGES_*.md`; all
outside `src/`, `tests/`, mypy scope, ruff scope).

## Why this sub-block

Per PROMPT_30 design: final Phase B docs closure pairs naturally с B.6.1
CHANGELOG consolidation. Atomic shipping signal — marks Phase B mediakit
workstream as release-ready.

BL-090 added per Marina addendum during STOP gate review — tracks the
hook-fires-on-Phase-A-boundary recurrence noticed across B.5 + B.6.2.

## Commit strategy

Single atomic `chore(docs)` commit per Phase A inventory recommendation.
Precedent observed:

- `376007d` `docs(backlog): add BL-082..085 ...` — bundled BACKLOG.md +
  CHANGES file в single commit (matches our pattern).
- `630b588` `docs(plan): refresh status overlay + branch HEADs ...` —
  PLAN-only, no CHANGES file (different scope — pure metadata refresh).

B.6.2 conceptually one atomic event (Phase B docs closure on one feature
branch + one merge); single commit reflects unit-of-work cleanly. Three
files staged together. No amend, no two-commit fixup.

## Not included (explicit defers)

- **`CHANGELOG.md`** — already updated в B.6.1 (PROMPT_29 commit
  `f479d1e`). B.6.2 не a public contract change — no [Unreleased] edit
  required.
- **Existing `CHANGES_*.md`** в `reports/docs-architect/discovery/` —
  append-only, не modified здесь.
- **Migrations** — pre-prod `0001_initial_schema.py` rule не triggered
  (no functional code changes).
- **CLAUDE.md / other governance docs** — no policy changes; engineering
  principles untouched.

## Verification

- `git diff --stat` summary: 2 modified + 1 new = `+183 / -5` lines net.
- `git status` post-edits: `BACKLOG.md` + `IMPLEMENTATION_PLAN_ACTIVE.md`
  modified, this CHANGES file untracked, plus pre-existing untracked
  `.claude/scheduled_tasks.lock` и `backups/` (out of scope, never
  staged).
- All 4 gates re-run post-edit: numbers bit-identical к Шаг 1 baselines.
- `git rev-parse main` still `e1c31b3` ✓ at all checkpoints (L43
  invariant preserved). This commit lands на `feature/b6-2-backlog-plan-overlay`,
  then `--no-ff` merged к `develop`.

## Phase B closure summary

After this merge, Phase B mediakit workstream is **complete на develop**:

- B.1 — `MediakitService` Pattern 1 strict rewrite + `comparison_service`
  migration (merge `a584351`)
- B.2 — owner-only PDF endpoint (merge `0308072`)
- B.3 — tests + counter refactor + `theme_color=None` hotfix (merge
  `49813f0`)
- B.4 — web_portal owner download button (merge `b47d5e2`)
- B.5.1 — advertiser-readable mediakit endpoint (merge `6961994`)
- B.5 — mini_app advertiser preview screen + ⓘ icon (merge `72ec2a1`)
- B.6.1 — CHANGELOG `[Unreleased]` consolidation (merge `2b0d0ab`)
- **B.6.2 — BACKLOG sweep + PLAN overlay (this commit, merge pending)**

Polish + future work tracked under explicit BL entries: BL-086, BL-087
(mediakit-specific), BL-088, BL-089 (frontend hygiene), BL-090 (workflow
infrastructure observation).

`main` remains at `e1c31b3` (v0.5.2) throughout — Phase B work entirely
on `develop`; release tag bump deferred to Marina decision.

## References

- PROMPT_30 — B.6.2 BACKLOG sweep + IMPLEMENTATION_PLAN overlay update.
- Phase A research: `tmp/b6_2_research.md` (BACKLOG/PLAN inventory, BL
  drafts, commit strategy precedent review).
- Marina addendum 2026-05-11 (BL-090 added during STOP gate review).
- Phase B CHANGES files (8 files): `CHANGES_2026-05-11_bl-078-precleanup-*`,
  `*-b1-*`, `*-b2-*`, `*-b3-tests-and-counter-refactor*`,
  `*-b3-theme-color-hotfix*`, `*-b4-*`, `*-b5-1-*`, `*-b5-*`.
- B.6.1 CHANGES: `CHANGES_2026-05-11_b6-1-changelog-unreleased.md`.

🔍 Verified against: feature/b6-2-backlog-plan-overlay HEAD (post-commit) | 📅 Updated: 2026-05-11
