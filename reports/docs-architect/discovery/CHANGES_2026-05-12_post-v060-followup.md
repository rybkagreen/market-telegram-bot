# CHANGES — post-v0.6.0 mini-followup

**Date:** 2026-05-12
**Branch:** feature/post-v060-followup
**Commit:** <sha after Шаг 7>

## Summary
Post-v0.6.0 release tidy. BL-090 entry extended with tree-state observation
from PROMPT_31 hook fire #8 natural resolution. IMPLEMENTATION_PLAN_ACTIVE.md
stale Phase B refs refreshed to v0.6.0 state. Docs-only commit, no functional
changes.

## Files touched
- `reports/docs-architect/BACKLOG.md` (BL-090 extension — +20 lines)
- `IMPLEMENTATION_PLAN_ACTIVE.md` (stale-ref refresh — 3 lines updated:
  L3 last-updated header, L62 main HEAD, L63 develop HEAD)
- `reports/docs-architect/discovery/CHANGES_2026-05-12_post-v060-followup.md`
  (new — this file)

## BL-090 extension content (verbatim summary)
- Tree-state vs commit-state observation: hook checks working-tree presence,
  natural resolution at develop→main merge boundary when CHANGES files
  propagate into target tree
- Pattern most active in Phase A read-only boundaries on feature branches
  without yet-committed CHANGES
- Observed fire totals: PROMPT_31 = 7, PROMPT_30 = 9, PROMPT_29 = 1+
- BL-016 silent-ignore protocol held cleanly across all — no autonomous
  capitulation
- Server-side mitigation (option (a)) reassessment: option (c)
  accept-as-known-harmless validated through full release cycle

## PLAN stale-ref changes
| Line | Before | After |
|---|---|---|
| L3 | `_Last updated: 2026-05-11 ... main @ e1c31b3 v0.5.2, develop @ 2b0d0ab pre-B.6.2-merge` | `_Last updated: 2026-05-12 ... main @ f866b2f v0.6.0, develop @ 2ad0759 post-release merge` |
| L62 | `main = e1c31b3 (v0.5.2 — T1.2.5f Bundle D + middleware fix)` | `main = f866b2f (v0.6.0 — Mediakit Phase B closure)` |
| L63 | `develop = 2b0d0ab (post-B.6.1 merge — [Unreleased] consolidation; B.6.2 docs closure merging now)` | `develop = 2ad0759 (post-v0.6.0 release merge — release/0.6.0 absorbed)` |

Historical-context refs in L46/L51/L54 (v0.5.0/0.5.1/0.5.2/2b0d0ab/49813f0
as event descriptions inside rolling closure notes) deliberately preserved
per scope discipline.

## tmp/ sweep (post-merge, Шаг 10)
Pattern-matched removals (7 files, ~880KB):
- `tmp/release_0_6_0_research.md`
- `tmp/release_v060_baseline.log`
- `tmp/release_v060_step6_gates.log`
- `tmp/release_v060_step9_gates.log`
- `tmp/release_v060_step13_gates.log`
- `tmp/b6_1_research.md`
- `tmp/b6_2_research.md`

Marina-discretion artifacts preserved: `web_portal_probe.md`,
`mini_app_probe.md`, `plan_metadata_apply_diff.md`, `plan_metadata_draft.md`,
`bl078_mediakit_probe.md`, plus older historical artifacts (PHASE3*,
T1_2_*, BL_NEW_ENTRIES, etc.).

## Baselines (preserved bit-for-bit)
- format-check: 0 errors / 401 files
- lint: 7 errors (baseline; ci-local exits 1 due to lint baseline as expected)
- typecheck: 0 errors / 293 files
- pytest: 0F / 1013P / 2S / 0E (7 runtime warnings — pre-existing,
  sentry/sqlalchemy/mock noise)

## Not included
- Other tmp/ files outside cleanup pattern (Marina discretion)
- No new BL entries; no closeouts of existing BL entries
- No CHANGELOG.md edit (v0.6.0 already cut; no public contract change)
- No main touching (release HEAD sacred at `f866b2f`)
- No tag operations

🔍 Verified against: feature/post-v060-followup
📅 Updated: 2026-05-12T09:23:00Z
