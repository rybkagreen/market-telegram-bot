# T1.2.1 — Auth refactor test-side cleanup

**Date**: 2026-05-04
**Branch**: `feature/t1-2-test-failures-cleanup` (created from `develop @ d68b302`)
**Commits**: T1.2.1.1 → T1.2.1.2 (1 fix + 1 docs)
**Origin**: T1.2.1 of T1.2 series (BL-072 T1.2 closure path). First sub-block;
quick-win starter per Marina Q1/Q6 sequencing decision.

## Summary

- `src/api/auth_utils.py` was previously refactored: `create_access_token`
  (single-arg legacy) replaced by `create_jwt_token` (4 args:
  `user_id`, `telegram_id`, `plan`, `source: JwtSource`). Test-side
  follow-through was missing, surfacing as 12 collection ImportErrors
  in ci-local (cluster P1 in T1.2 audit).
- T1.2.1.1 closes the migration with **1 file, +7/−2 lines**. Empirical
  scope is one inline-import in `tests/conftest.py:474`
  (`api_client_with_auth` fixture); the 3 test files cited by the audit
  have no direct imports — all ImportErrors fan out from this one
  fixture site.
- 9 ImportErrors cleared (not 12 as audit predicted — audit miscounted
  cluster C7 by 3 entries; see "Audit correction" below).
- Per Marina decisions: `source="mini_app"` (dominant test pattern;
  fixture is generic); `plan=advertiser_user.plan` (User-model default
  `"free"`, verified at `src/db/models/user.py:58`); `telegram_id`
  pulled from `advertiser_user`.

## Files modified

- `tests/conftest.py:472–484` — `api_client_with_auth` fixture body.
  Old: `from src.api.auth_utils import create_access_token; token =
  create_access_token(advertiser_user.id)`. New: `from
  src.api.auth_utils import create_jwt_token; token =
  create_jwt_token(advertiser_user.id, advertiser_user.telegram_id,
  advertiser_user.plan, source="mini_app")`.

No production source code touched. `src/api/auth_utils.py` was the
upstream refactor that triggered this work; it was already at its
current shape on `d68b302` and remains untouched in T1.2.1.

## Marina decisions inherited (T1.2 series Q-table)

| # | Decision | Applied in T1.2.1 |
|---|----------|-------------------|
| Q1 | Split ordering T1.2.1 → 2 → 3 → 4 → 5 → 6 | T1.2.1 first ✓ |
| Q6 | Quick-win starter = T1.2.1 | This sub-block ✓ |
| Q8 | Per-sub-block re-baseline cadence | Recorded below ✓ |
| Branch | Single feature branch for T1.2 series | `feature/t1-2-test-failures-cleanup` ✓ |
| 1.B (1) | Audience: `mini_app` | Applied ✓ |
| 1.B (2) | Scope: 1 file (audit correction) | Applied ✓ |
| 1.B (3) | `plan` arg: `advertiser_user.plan` (verify default first) | Verified `User.plan` default = `"free"`; applied ✓ |
| 1.D (3) | (c) hybrid commit + corrected message + audit correction in T1.2.1.2 | Applied ✓ |

## Verification — baseline at branch HEAD

| Gate | Baseline `d68b302` | After `69f1490` (T1.2.1.1) | After `<HEAD>` (T1.2.1.2) |
|------|--------------------|----------------------------|----------------------------|
| ci-local FAILED | 81 | 86 | 86 |
| ci-local PASSED | 940 | 940 | 940 |
| ci-local SKIPPED | 6 | 10 | 10 |
| ci-local ERROR | 17 | 8 | 8 |

T1.2.1.2 is docs-only — does not change the test gate. Counts
preserved by construction.

### Causal breakdown of T1.2.1.1 delta

- **−9 ERROR** (caused by edit) — ImportError fan-out cleared:
  - 5 in `tests/test_api_channel_settings.py` (cluster C8)
  - 4 in `tests/test_api_placements.py` (no cluster ID — auth-only file)
- **+5 FAIL** (latent, unmasked by edit) — pre-existing assertion drift
  in `tests/test_api_channel_settings.py` (C8 second-half handoff).
  These tests previously errored on fixture setup; with the auth fix
  they reach test bodies and reveal real failures.
- **+4 SKIP** (latent, unmasked by edit) — `tests/test_api_placements.py`
  tests have skip-conditions in their bodies that were unreachable
  while setup errored.
- **8 ERROR residual** — ALL in `tests/test_counter_offer_flow.py`,
  ALL fixture-name (`'test_advertiser'` / `'test_owner'` /
  `'test_channel'` not found). Cluster C7, T1.2.2 territory.

Total tests preserved: 1044 → 1044 (no tests added/removed).
9 cleared ERRORs accounted for: 5 → FAIL + 4 → SKIP.

## Audit correction (absorbed per Marina 1.D (c) hybrid decision)

The original T1.2 audit's cluster shape estimates were off in two places.
These are recorded here so T1.2.2-T1.2.6 plans can re-baseline against
empirical reality, not paper estimates.

### Cluster C7 — `tests/test_counter_offer_flow.py` (8 errors)

| | Audit | Reality |
|--|-------|---------|
| ImportError count | 3 | **0** |
| fixture-name count | 5 | **8** |

All 8 entries are fixture-name (`test_advertiser` / `test_owner` /
`test_channel` not found). None were ever ImportError-driven.
Audit's "3 ImportError + 5 fixture-name" decomposition was an
artifact — the file consumes `api_client_with_auth` but its 8
ERRORs all originated from missing module-level fixtures, not from
the conftest auth import. Full C7 closure now belongs to T1.2.2.

### Cluster C8 — `tests/test_api_channel_settings.py` (5 entries)

Audit listed 5 ERRORs. After T1.2.1.1 they become **5 FAILs** — same
cluster, post-unblock signal. The transition is causally clear:
ERROR was setup-stage propagation from broken auth fixture; once
fixture compiles, test body executes and asserts against reality
(which currently disagrees). T1.2.2 must investigate these 5 failures
and decide per-test whether they reveal a real production bug or a
test-side staleness.

### Cluster sizing impact on T1.2 cumulative arithmetic

| | Audit-stated | Empirical (post-T1.2.1) |
|--|--------------|--------------------------|
| T1.2.1 entries closed | 12 | **9** |
| T1.2.2 entries to close (C7) | 5 | **8** (+3 shifted from T1.2.1) |
| T1.2.2 entries to close (C8) | 5E | **5F** (same count, different bucket) |
| Cumulative T1.2 progress after T1.2.1 | 12/99 (12%) | **9/99 (~10%)** |

Net entries (99) preserved; only T1.2.1 ↔ T1.2.2 boundary shifted.

## T1.2.2 handoff note (explicit)

Marina decision: T1.2.2 must investigate the **5 unmasked FAILs** in
`tests/test_api_channel_settings.py` as part of cluster C8 work. The
5 tests:

- `TestAPIChannelSettings::test_get_creates_defaults`
- `TestAPIChannelSettings::test_patch_price`
- `TestAPIChannelSettings::test_patch_invalid_price_422`
- `TestAPIChannelSettings::test_patch_invalid_time_order_422`
- `TestAPIChannelSettings::test_patch_partial_no_side_effects`

For each: classify root cause as either (a) test-side staleness (test
expectation outdated, fix the test) or (b) real production bug (test
correctly catches a regression in `src/api/routers/channel_settings.py`
or `ChannelSettingsRepo`/service layer). Per P3/P5: **flag any
production bugs as Возражения in the T1.2.2 closure CHANGES** — do
not silently fix production code in a "test failures cleanup" commit.

## L44 candidate (lessons learned)

**Audit cluster classifications can be wrong even after deep dive —
empirical edit reveals true shapes.**

Why: the T1.2 audit (Phase A/B research per P2) was thorough enough
to enumerate 99 entries across 20 clusters but classified C7's 8
entries as "3 ImportError + 5 fixture-name" by assumption (file
*does* consume an auth fixture, *and* references missing fixtures —
both observed, decomposition guessed). The single empirical
edit in T1.2.1.1 immediately corrected the classification: 0+8, not
3+5. **Implication:** for clusters that look mixed at audit time,
budget at-edit-time re-classification rather than treating the audit
decomposition as load-bearing for cumulative arithmetic.

How to apply: at T1.2.2-T1.2.6 entry, run the empirical edit first
(or a smaller probe edit) and re-baseline cluster sizes against the
result before locking the closure CHANGES arithmetic. Re-baseline
is per-sub-block (Q8) and absorbs corrections — exactly the pattern
this CHANGES file uses.

Candidate name: **L44 — empirical re-baseline beats paper decomposition**.
Tier 2 closure batch entry, not inline-edit (per BL-076 process
discipline).

## Возражения и риски

None blocking T1.2.1 closure. Two observations for series-level
attention:

1. **Audit confidence calibration.** C7 miscount + C8 ERROR→FAIL
   transition were not caught at audit time despite Phase A/B research.
   Future T1.2 sub-blocks should treat audit decomposition as a
   working hypothesis, not a contract. Re-baseline first, plan
   second. (Not a fix-commit item; series-level lesson.)

2. **5 unmasked FAILs may include real production bugs.** Until
   T1.2.2 investigates, the C8 FAILs sit on `feature/t1-2-...`
   without a verdict. If any of the 5 reveal a regression in
   `channel_settings` router or its service/repo, the bug
   pre-existed T1.2.1 (was masked by setup error) — not introduced
   by this branch. T1.2.2 owns the investigation.

## Cross-references

- T1.2 audit (Phase A/B output): `tmp/T1_2_FAILURES_AUDIT_2026-05-04.md`
- Prior closure (Phase 3c.1): `CHANGES_2026-05-04_phase3c-1-transition-wiring.md`
- BL-072 T1.2 entry: `reports/docs-architect/BACKLOG.md`
- Auth source: `src/api/auth_utils.py:100` (`create_jwt_token`),
  `src/api/auth_utils.py:135` (`decode_jwt_token`),
  `src/api/auth_utils.py:22` (`JwtSource = Literal["mini_app", "web_portal"]`)
- Audience routing: `src/api/dependencies.py:27` (`_ALLOWED_AUDIENCES`)

🔍 Verified against: `d68b302` (develop) | `69f1490` (T1.2.1.1) | 📅 2026-05-04
