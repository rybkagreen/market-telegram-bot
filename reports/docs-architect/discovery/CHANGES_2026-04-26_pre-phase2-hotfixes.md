# CHANGES — 2026-04-26 — Pre-Phase-2 Hotfixes

## Summary

Three pre-Phase-2 hotfixes (T1-3, T1-5, T1-7 from PHASE2_RESEARCH_2026-04-26.md)
plus two verify artifacts (T2-2, correlation_id origin) merged via
fix/placement-pre-phase2 → main → develop. Independent of Phase 2 — these are
existing bugs and verification questions whose resolution had to precede
the § 2.B.0 alignment commit.

## Commits

- `c6123c1` fix(placement): unify expires_at to +24h across counter_offer
  and pending_payment paths (T1-3)
- `8f7ebe7` test(placement): regression guard for published-only
  check_scheduled_deletions filter (T1-5 — filter already in place since
  8c66a23a, this commit adds source-text + compiled-SQL guard tests)
- `781f8c9` chore(tasks): remove archive_old_campaigns — never-fired
  data-loss bug (T1-7)
- `c7116a2` docs(phase-2): pre-alignment verify steps T2-2 and
  correlation_id

## Verify Outcomes

- **T2-2 retry_failed_publication** → DEAD. Six references in
  placement_tasks.py + one aspirational mention in AAA-06; zero
  dispatchers; not in Beat schedule. To be deleted in alignment commit.
- **correlation_id origin** → STUB-IN-DOCSTRING. No middleware sets it,
  no consumers exist. Field stays in TransitionMetadata schema with
  explicit "RESERVED — Phase 3 wiring" docstring; cheaper than a future
  schema bump.

## Mypy Baseline

Verified post-merge: `Found 10 errors in 5 files (checked 273 source files)`
on both main and feature branch — matches PF.1 baseline 10/5/272+1
(+1 source file added since Phase 0).

Ruff baseline drift identified separately — see BL-007 (working tree).

## Public Contract Delta

None. Hotfixes are existing-code bug fixes; no API/schema/contract change.
CHANGELOG [Unreleased] entry below documents the behavioural fix to
expires_at semantics for forward-compatibility documentation only.

## Origins

- T1-3, T1-5, T1-7 from `PHASE2_RESEARCH_2026-04-26.md` Tier 1.
- Verify steps T2-2 and correlation_id from same report § 8 prerequisites.
- Промт-1 (`PROMPT_1_pre_phase2_hotfix.md`) execution log.

🔍 Verified against: `c7116a2` (fix/placement-pre-phase2 tip merged via d5075ab) | 📅 Updated: 2026-04-26
