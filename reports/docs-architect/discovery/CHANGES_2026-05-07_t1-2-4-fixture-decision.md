# T1.2.4 — unit fixture decision (Phase C closure)

**Date:** 2026-05-07
**Branch:** feature/t1-2-test-failures-cleanup
**Predecessor:** T1.2.3.4 closure @ 1083c22
**Baseline (pre-Phase-C, ci-local):** 69F / 965P / 14S / 0E (drift +1F vs Phase A+B 68F)
**Final (post-Phase-C, ci-local):** 53F / 987P / 12S / 0E
**Δ Phase C:** −16F +22P −2S
**Cumulative T1.2 progress:** ~48/99 entries closed (~48%)

## Marina decisions (consolidated)

| Q | Resolution | Rationale |
|---|---|---|
| Q1 | (i) — refactor xp_service src/ | S-48 violation fixed at source |
| Q2 | α — extend api_client_with_auth с DB override | Single fixture edit vs 12+ caller edits |
| Q3 | (a) — C10 1S keep с pointer | mediakit prod bug deferred to T1.2 final closure BACKLOG |
| Q4 | (b) — split per-cluster commits | Granular history |
| Q5 | (b) — split TestStreakBonus в new file | Commit cleanliness |
| Q6 | (i') — full xp_service refactor (4+ methods + 3 callers) | Architectural-purity > scope containment |
| Q7 | informational | test_streak_bonus_below_threshold PASSED before/after — clean regression |
| Q8 | (α) — full-flow integration через billing_service | Match production path; tests catch future contract regressions |
| Q9 | informational | Phase A+B 7-test count was correct; relocation surfaced INV-1 violations |
| Q10 | (a) — fixture α as standalone commit | Diagnostic value: real failure causes visible |
| Q11 | hybrid (ii') — D + A fix, B defer to T1.2.4b | Scope management |
| Q12 | continue reorder 1→2→4→3→5→6 | Quick wins consolidated before C4 |

## Cluster summary

### C5 (commit cfa8d35) — relocate test_escrow_payouts + integrate billing flow

- **Δ:** −7F +7P (4 SQLite-shadow F + 3 P preserved through relocation)
- **Phase A+B mis-classification:** "BillingService Pattern 1, fixture SQLite shadow only blocker"
  → **Reality:** BillingService Pattern 1 ✓, but 4 tests inserted placement directly с
  `status=PlacementStatus.escrow` без `escrow_transaction_id`, violating INV-1 invariant
  (placement_escrow_integrity CHECK constraint enforced на pg-testcontainer, not on SQLite shadow)
- **Side fix:** test_release_escrow_funds_success had stale assertion
  `mailing.status == MailingStatus.paid` — that side effect was deliberately removed in
  commit f20f51c (idempotency migration MailingLog → Transaction.idempotency_key)
- **Side fix:** test_refund_failed_placement_success needed explicit `db_session.flush()`
  before refresh; refund_failed_placement does not flush internally
- Helper extracted: `_setup_escrow_placement` exercises real pending_payment → escrow
  flow via `freeze_escrow_for_placement` + `PlacementTransitionService`

### C10 (commit 8d4d0c6) — relocate test_bmediakit_comparison + thread session arg

- **Δ:** −3S +3P; 1S kept (Q3=a — mediakit production bug deferred)
- 3 SQLite-skipped tests in TestComparisonService closed via relocation + `session=db_session`
- 1 test (test_get_mediatkit_data) keeps `@pytest.mark.skip` с refreshed pointer:
  `mediakit_service stale fields production bug — defer to T1.2 final closure BACKLOG batch (Q3=a)`
- **Side fix:** 2 originally-passing tests (test_get_or_create_mediatkit, test_update_mediatkit)
  called mediakit_service without session — masked under SQLite shadow, surfaced as
  ConnectionRefused under pg-testcontainer
- **Side fix:** assertion key drift in 2 tests — service returns `subscribers` (not
  `member_count`), `last_er` (not `er`), `recommendation.channel_id`. Skip markers had
  been hiding stale keys

### C8 (commits 6417037 + 6903009 + a06c6dd) — fixture α + mechanical fixes + defer

- **Δ:** −7F +6P +1S (fixture α set-up commit alone closed 0F but enabled diagnosis;
  mechanical 4b closed 6F; 4c skipped 1F deferred to T1.2.4b)
- **Phase A+B mis-classification:** "C8 = 12F ConnRefused" → **Reality:** 7F с 4 root causes:
  - (D) Stale URL paths `/api/v1/placements/` vs real `/api/placements/` (2F)
  - (A) Wrong user fixture: tests for channel-settings used advertiser_user but
    router checks `channel.owner_id == current_user.id` (3F)
  - (C) Stale default value 500 → 1000 (1F; originally classified as schema field drift)
  - (B) Pydantic Decimal 422 serialization bug (1F; deferred to T1.2.4b)
- **4a — fixture α infrastructure:** `api_client_with_auth` now overrides
  `get_db_session` + `get_current_user{,_from_mini_app,_from_web_portal}`. Cleanup on
  yield exit prevents cross-test pollution
- **4b — mechanical:** D URL fix + new `api_client_with_owner_auth` fixture +
  default value drift fix
- **4c — explicit defer:** `test_patch_invalid_price_422` skipped с T1.2.4b pointer

### C4 (commit ae872a1) — xp_service Pattern 1 refactor

- **Δ:** −1F +5P (test_streak_bonus_thresholds 1F→1P + 4 new regression tests)
- 6 of 7 xp_service async methods refactored: removed `async with session.begin()`,
  removed `async with async_session_factory()`, all accept `session: AsyncSession` arg
- 2 latent commit bugs fixed by-product:
  - `add_advertiser_xp` previously `flush()` without commit → silent rollback
  - `add_owner_xp` same pattern
  - Pattern 1 removes flush/commit responsibility from service entirely
- 3 src/ callers updated:
  - `src/tasks/notification_tasks.py` notify_owner_xp_for_publication: opened own session
    via `celery_async_session_factory` + commit (Pattern 2 caller)
  - `src/tasks/gamification_tasks.py` _process_streak_continue: parent task session
    threaded через `_update_user_streak` chain
  - `src/tasks/gamification_tasks.py` award_daily_login_bonus: task session passed
    directly; `flush()` replaced с `commit()` (Pattern 2 caller)
- Test split: TestStreakBonus class moved tests/unit/test_gamification.py →
  tests/test_streak_bonus.py
- 4 new regression tests document Pattern 1 commit semantics
- badge_service.award_badge is also Pattern 2 (out of scope for Q6=(i')) — monkeypatch'd
  in test_streak_bonus_thresholds to avoid ConnectionRefused on 30+/100+ thresholds

## Lessons learned

### L50 — xp_service S-48 violation surface area (T1.2.4 Phase A+B + Phase C Šаг 0)

Phase A+B probe identified C4 single failing test и classified root cause як
«xp_service Pattern 2 violation». Phase A+B inventory was shallow:

- File path extracted from pytest output as if test file → was actually method name
  within `test_gamification.py::TestStreakBonus`
- Only failing method audited; rest of class и file ignored
- Only mentioned method's Pattern 2 documented; sibling methods in same xp_service.py
  не inspected
- src/ callers не enumerated

Phase C Šаг 0 (mandatory before mutation per L43) revealed:

- 6 of 7 xp_service async methods are Pattern 2 violations, не just one
- 3 src/ callers in production Celery tasks
- 2 latent commit bugs in `add_advertiser_xp`/`add_owner_xp` (silent rollback)
- Sibling test `test_streak_bonus_below_threshold` in same TestClass also exercises the
  violation

**Lesson:** для S-48 violation candidate clusters, Phase A+B probe must do **full
surface area inventory**:

1. List ALL methods in target service file (not just one which surfaced)
2. Classify each method: Pattern 1 / Pattern 2 / Pattern 3 / read-only
3. List ALL src/ callers across grep targets (`src/tasks/`, `src/api/`, `src/bot/`,
   `src/services/`)
4. Verify file path empirically (`find tests/ -name <file>`) перед claim
5. Inspect surrounding TestClass siblings — they often share same fixture/violation
   pattern

This rule applies к BL-019 cleanup workstreams и any future S-48 sweeps.

### L51 — Auth dep bypasses FastAPI DI via async_session_factory()

`_resolve_user_for_audience` in `src/api/dependencies.py:86` opens its own session
via `async_session_factory()` directly, bypassing FastAPI's `Depends(get_db_session)`
DI. This is invoked by `get_current_user` / `get_current_user_from_mini_app` /
`get_current_user_from_web_portal` — все three "current user" deps used by routers.

Implication: overriding `get_db_session` in test fixture is **insufficient** for API
tests — auth dep still hits real PG via async_session_factory. Tests must also override
all three user resolvers to inject test user directly.

**Lesson:** auth dep architecture has direct-call to async_session_factory bypassing DI.
Tests requiring isolated session must override BOTH `get_db_session` AND the user
resolvers. Future architectural cleanup candidate (refactor `_resolve_user_for_audience`
to accept session via DI) — out of T1.2 scope; tracked in T1.2.4b alongside (B) Pydantic
422 bug.

### L52 — Phase A+B classification methodology: separate data-collection from interpretation

C5, C8, C10 all had Phase A+B count or root-cause mis-classifications surfaced during
Phase C verification:
- C5: claimed "SQLite missing tables" — real cause was INV-1 violation surfacing under pg
- C8: claimed "12F ConnRefused" — real was 7F с 4 distinct latent-bug root causes
- C10: claimed 3S only need fix — surfaced 2 originally-passing tests breaking under
  pg-testcontainer + assertion key drift

**Lesson:** Phase A+B classifications based on error-string match are insufficient.
Phase C step 0 isolated verification before mutation is mandatory; Auto-continue
mode rule (h) explicitly STOPs on classification mismatch.

**Rule strengthening:** Phase A+B probe ships **raw failure data** (full traceback,
isolated run logs per cluster, surface inventory listing) — **classification happens
in Phase C Šаг 0**, not in Phase A+B output. Separates data-collection from
interpretation:

- Phase A+B output: cluster bucketing by file/test (count) + raw error tracebacks +
  isolated `pytest -v --tb=long` log per representative test + service-file surface
  inventory if S-48-adjacent
- Phase C Šаг 0 output: per-cluster classification (root cause, blast radius,
  fix scope) BEFORE any mutation. STOP-on-mismatch против Phase A+B raw data is
  expected, not exceptional

This avoids "credibility hand-off" where Phase C agent inherits unverified Phase A+B
interpretation as truth.

### L53 — Phase A+B credibility decay (overarching pattern from T1.2.4)

T1.2.4 sub-block surfaced **4 strikes** of Phase A+B classification inadequacy across
4 clusters:

1. **C4 path strike:** plan referenced `tests/unit/test_streak_bonus_thresholds.py`;
   file did not exist (test was actually method in `test_gamification.py::TestStreakBonus`)
2. **C4 surface strike:** plan classified single Pattern 2 method; reality 6/7 methods
   + 3 src/ callers + 2 latent commit bugs
3. **C5 root-cause strike:** plan claimed "SQLite missing tables fixture blocker";
   reality INV-1 placement_escrow_integrity violations + stale assertions
4. **C8 count + classification strike:** plan claimed "12F ConnRefused"; reality 7F
   with 4 distinct root causes (URL drift / wrong user fixture / stale default /
   Pydantic 422 bug)

**Pattern:** Phase A+B probe methodology is systematically inadequate для S-48-adjacent
or integration-fixture clusters. Error-string clustering matches surface symptoms but
misses underlying causes (constraint violations, schema drift, framework bypass paths).

**Mitigation:** Future probes targeting S-48 / integration / fixture-pattern clusters
must adopt L52 rule (raw data + Phase C classification). L43 mandatory Šаг 0 isolated
verify-per-cluster is not optional — it is the **primary** classification layer; Phase
A+B is supporting data only.

This rule applies к T1.2.5 (deprecated tests delete batch — likely OK, low-risk),
T1.2.6 (publication_service / billing_service.release_escrow / disputes — high-risk
S-48 territory), and T1.2.4b (Pydantic 422 bug + auth-DI refactor — production-bug
territory).

## Deferrals

### To T1.2.4b explicit next sub-block

- **C8-B:** test_patch_invalid_price_422 — Pydantic Decimal serialization in 422 responses
  returns 500. Affects all endpoints with Decimal `ge`/`le` validation params. Requires
  exception handler in `src/api/main.py` + sweep.
- **Auth-bypass-DI:** refactor `_resolve_user_for_audience` to accept session via FastAPI DI
  (currently uses `async_session_factory()` directly).

### To T1.2 final closure → BACKLOG (consolidate, не inline)

- **C10-1S:** mediakit_service stale fields production fix
  (`chat.last_avg_views` / `last_post_frequency` / `price_per_post` model migrated;
  service still reads old field names)
- **xp_service helpers:** badge_service.award_badge is also Pattern 2 (opens own session
  via async_session_factory). Out of T1.2.4 Q6=(i') scope. Future S-48 sweep candidate.

## Open для T1.2.5 (next sub-block)

- Deprecated tests delete batch
- C20 main_menu (`tests/unit/test_main_menu.py` currently `--ignore`d in Makefile)
- C15 (`tests/test_channel_settings_repo.py`) — decision pending: rewrite vs delete

## Commit chain

| # | SHA | Cluster | Type |
|---|---|---|---|
| 1 | cfa8d35 | C5 | test |
| 2 | 8d4d0c6 | C10 | test |
| 3 | 6417037 | C8 4a fixture α | test |
| 4 | 6903009 | C8 4b D+A | test |
| 5 | a06c6dd | C8 4c B defer | test |
| 6 | ae872a1 | C4 xp_service | fix |

🔍 Verified against: `1083c22` (predecessor) → `ae872a1` (this closure) | 📅 Updated: 2026-05-07T00:00:00Z
