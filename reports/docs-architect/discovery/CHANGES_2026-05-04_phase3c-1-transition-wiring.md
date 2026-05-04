# Phase 3c.1 — Transition-time gate enforcement wiring

**Date**: 2026-05-04
**Branch**: `feature/phase3c-transition-wiring` (created from `develop @ 64a0043`)
**Commits**: 3c.1.1 → 3c.1.3 (1 feat + 1 test + 1 docs)
**Origin**: Phase 3c — closes BL-072 T1.1 paper-only. Wires
`LegalComplianceService.check_gates_for_transition` into
`PlacementTransitionService.transition` body so every organic transition
that leaves the allow-list also satisfies its compliance preconditions.
Phase 3b's gate framework (5b.1-5b.7d) becomes load-bearing at runtime.

## Summary

- 3c.1 wires gate dispatch into `transition()` body — after allow-list,
  before `_apply()` mutation. Failed gates raise `TransitionBlockedError`
  with a collect-all blockers list and write an `AuditLog` row.
- `bypass_gates: bool = False` keyword-only parameter on `transition()`
  for admin/test contexts (Q2 explicit signature opt-out, never DB lookup).
- `transition_admin_override` remains gate-free by design — admin path
  is the universal carve-out (O.7 architectural contract locked by test).
- Caller updates bundled (5 sites): 3 G07-affected user-facing handlers
  with marker-aware UX classifier (`bot/utils/gate_block_render.py`),
  2 publication-side defensive try/except blocks.
- `tests/integration/test_expires_at_consistency.py:100` per-test
  `monkeypatch` of `check_gates_for_transition` (reverts to no-op
  for that test only — pre-Phase-3c fixture predates G07 marker).
- Baselines preserved: `make ci-local` 81F / 940P / 6S / 17E
  (vs baseline 81F / 922P / 6S / 17E → +18 new passing tests).
- 0 schema work; `pending_gate_resolutions` JSONB persistence deferred
  to Phase 3d UI requirement (Q5=(a)).

## Files modified

- `src/core/services/placement_transition_service.py` — `transition()`
  gains keyword-only `bypass_gates: bool = False`; gate-check block
  inserted after allow-list and before `_apply()`. `TransitionBlockedError`
  raised with `extra={"from", "to", "blockers": [...]}`. AuditLog row
  written before raise. Imports: `TransitionBlockedError`,
  `LegalComplianceService`, `AuditLogRepo`. Docstring updates on both
  `transition()` and `transition_admin_override()`.
- `src/bot/utils/gate_block_render.py` (NEW) — shared marker vs.
  real-fail classifier (`is_marker_only`, `render_owner_message`,
  `render_advertiser_message`). PHASE_N_PENDING markers render
  "временно недоступно"; real-fail blockers render gate names and the
  first non-null `remediation_url`.
- `src/bot/handlers/owner/arbitration.py:218` — `accept_request`
  callback wraps `transition()` call with `try/except TransitionBlockedError`;
  blocked path calls `render_owner_message` and uses `callback.message.answer`.
- `src/bot/handlers/advertiser/campaigns.py:204` — `camp_counter_accept`
  callback mirrors arbitration — `render_advertiser_message` rendering
  on block.
- `src/tasks/notification_tasks.py` (auto_approve_24h) — Celery task gains
  marker-aware classification: counters `skipped_marker_count` /
  `skipped_real_fail_count`, debug log for markers, warning log for
  real-fail, summary log emitted at end. Iteration continues across
  blocked placements.
- `src/core/services/publication_service.py` — defensive try/except on
  both transition sites: escrow→published (line ~321) on gate-block
  transitions placement to `failed` (allow-listed gate-empty path);
  published→completed (line ~424) leaves placement in `published` for
  next post-publication verification cycle.
- `tests/integration/test_expires_at_consistency.py` — adds
  `monkeypatch` parameter and per-test setattr of
  `LegalComplianceService.check_gates_for_transition` to bypass the
  G07 marker for the legacy fixture.
- `tests/integration/test_placement_transition_service.py` — adds
  `TestGateEnforcement` class (9 tests).
- `tests/unit/test_bot_arbitration_owner_accept.py` (NEW) — 3 tests
  (happy / marker / real-fail).
- `tests/unit/test_bot_advertiser_pay_now.py` (NEW) — 3 tests (mirror).
- `tests/unit/test_notification_auto_approve_skips_blocked.py` (NEW) —
  3 tests (marker-only, real-fail, multi-placement iteration).
- `CHANGELOG.md` — Unreleased section appended.
- `reports/docs-architect/discovery/CHANGES_2026-05-04_phase3c-1-transition-wiring.md`
  (NEW — this file).
- `IMPLEMENTATION_PLAN_ACTIVE.md` — Phase 3c status overlay.
- `reports/docs-architect/BACKLOG.md` — BL-072 T1.1 closed
  (paper-only); BL-075 new entry for `_TRANSITION_GATES` G01-G06 gap.

## Commits

| # | Hash | Title |
|---|---|---|
| 3c.1.1 | `075637a` | feat(transitions): wire LegalComplianceService gate enforcement into transition() |
| 3c.1.2 | `e71a676` | test(transitions): comprehensive gate enforcement coverage (service + callers) |
| 3c.1.3 | (this commit) | docs(phase3c): 3c.1 closure — transition-time gate enforcement wiring |

## Phase A+B+C trace

Phase A+B artifact: `tmp/PHASE3C_INVESTIGATION_2026-05-04.md`. Findings
driving Phase C decisions:

- **A.1 — `transition()` body audit.** Confirmed zero compliance refs
  in `placement_transition_service.py` at HEAD `64a0043`. Pattern 1
  S-48 contract (caller-owns session) — preserved verbatim through
  Phase 3c.
- **A.2 — `_TRANSITION_GATES` table.** 18 entries mirror `_ALLOW_LIST`;
  4 entries non-empty: G07 markers on `pending_owner|counter_offer →
  pending_payment`; G08/G09/G10 real bodies on `escrow → published`;
  G11/G12 on `published → completed`. Remaining 14 entries gate-empty.
- **A.4 — Caller catalog.** 28 organic + 1 admin-override. 6 sites
  hit G07-affected transitions (3 user-facing + 3 service-internal),
  2 hit publication-side gates, 20 gate-empty.
- **A.4 — `TransitionBlockedError` already defined.** `core/exceptions.py:231-239`
  pre-existed; 3c.1 only imports + raises (no class authoring).
  `RekHarborError` global handler maps to HTTP 409 with structured payload.
- **A.10 — Audit log column constraint.** `audit_logs.action: String(20)`
  — `transition_blocked` (18 chars) fits.
- **A.13 — Test infrastructure surface.** `db_session` fixture wraps
  per-test transaction in connection-bound rollback (BL-024 load-bearing
  infrastructure preserved untouched). `monkeypatch` is per-test
  scope — does not leak.
- **B.6 — Q6 critical decision.** G07 PHASE4_PENDING firing under wiring
  halts production placements until Phase 4 ships G07 real body.
  Marina decision: **Q6=(a) accept blocker**. Service stays "pure
  blocking" — no reason_code-aware filter at service level. Marker vs.
  real-fail distinction lives at caller layer (UX rendering, log
  severity), not in `transition()` body. Caller pattern: helper
  `is_marker_only()` returns True iff every blocker has
  `reason_code in {phase4_pending, phase5_pending}`.

## Marina decisions (Q1-Q7 from Phase B.6)

| # | Question | Decision |
|---|---|---|
| Q1 | Scope split | **(а)** Alpha — single 3c.1, 3 commits |
| Q2 | Admin carve-out at organic path | **(а)** `bypass_gates: bool = False` keyword-only param (explicit signature opt-out) |
| Q3 | Multi-blocker UX | **(а)** collect-all (mirrors 5b.7a precedent) |
| Q4 | Audit log integration | **(а)** YES, action=`"transition_blocked"` |
| Q5 | `pending_gate_resolutions` schema | **(а)** NOT persist — defer to Phase 3d UI need-trigger |
| **Q6** | **G07 PHASE4_PENDING runtime implication** | **(а)** Accept blocker — service blocks on every `not r.passed`. Caller-side classification handles marker vs. real-fail UX. |
| Q7 | New GateReason entries | NONE |

## Q6 implication (Known constraint until Phase 4)

Phase 3c ships gate enforcement for production. **Side effect:** every
`pending_owner | counter_offer → pending_payment` transition now blocks
on G07 PHASE4_PENDING marker until Phase 4 (T1.6) ships the real G07
evaluator (МES Acts API + КЭП verification).

**What that means in practice:**

- Owner clicks "Accept" in Telegram bot → `accept_request` raises
  `TransitionBlockedError` → user sees "⏳ Подтверждение временно
  недоступно — идёт настройка системы." No remediation list (gate names
  hidden when marker-only).
- Advertiser clicks "Accept counter-offer" → mirror UX.
- Celery beat `auto_approve_24h` → `skipped_marker_count` increments
  per blocked placement; debug log only (no warning noise).
- API `POST /api/placements/{id}/transition` → HTTP 409 with
  `error_code: "transition_blocked"` and `extra.blockers[0].reason_code:
  "phase4_pending"`.

This is **deliberate and expected** until Phase 4 lands. Phase 3c
closes T1.1 (gate framework wiring) but **NOT** the production-readiness
gap. The full gap closure is bundled with Phase 4 G07 real body landing.

## Test coverage

### Service-layer (tests/integration/test_placement_transition_service.py)

`TestGateEnforcement` (9 cases):

1. `test_g07_marker_blocks_pending_payment_transition` — pending_owner→pending_payment
   raises with G07 marker blocker; placement.status NOT mutated.
2. `test_gate_empty_transition_passes_through` — pending_owner→counter_offer
   succeeds (gate-empty entry).
3. `test_admin_override_bypasses_gates` — `transition_admin_override`
   succeeds even on a G07-affected transition.
4. `test_bypass_gates_flag_skips_check` — `transition(..., bypass_gates=True)`
   skips evaluation entirely.
5. `test_blockers_audit_log_written` — AuditLog row written with
   `action="transition_blocked"`, `resource_type="placement"`,
   resource_id, user_id, and structured `extra`.
6. `test_failed_transition_no_status_mutation` — placement.status
   preserved after `TransitionBlockedError`.
7. `test_failed_transition_no_history_row` — no PlacementStatusHistory
   row appended after raise.
8. `test_multi_blocker_collect_all` — escrow→published collects G08+G09+G10
   blockers into `extra.blockers[]` (collect-all proven on 3-gate path).
9. `test_publication_side_g08_g09_g10_pass_with_full_seed` — same
   transition succeeds when OrdRegistration + erid seeded (real-now
   bodies pass under correct setup).

### Caller-layer

`tests/unit/test_bot_arbitration_owner_accept.py` (3 cases):
happy / marker_blocked / real_fail_blocked.

`tests/unit/test_bot_advertiser_pay_now.py` (3 cases): mirror.

`tests/unit/test_notification_auto_approve_skips_blocked.py` (3 cases):
marker-only blockers + debug log; real-fail + warning log; iteration
continues across mixed-result placements.

## Verification

| Gate | Baseline @ 64a0043 | Post-3c.1 |
|---|---|---|
| ruff (`src/`) | 4 | 4 |
| ruff (`src/ tests/`) | 20 | 20 |
| ruff format-check | 9 files non-conformant | 9 files non-conformant |
| pytest unit | 62F / 642P / 1E | 62F / 660P / 1E (+18) |
| `make ci-local` aggregate | 81F / 922P / 6S / 17E | 81F / 940P / 6S / 17E |

Net: 0 regressions; +18 new passing tests; pre-existing baseline noise
preserved (BL-007 / BL-019 known).

## Cross-references

- Phase 3b master closure: `CHANGES_2026-05-03_phase3b-closure-batch.md`
- 5b.7a precedent (channel-add hook): `CHANGES_2026-05-03_phase3b-5b7a-channel-add-hook.md`
- 5b.7d marker semantics: `CHANGES_2026-05-03_phase3b-5b7d-marker-uniformization.md`
- Phase A+B investigation: `tmp/PHASE3C_INVESTIGATION_2026-05-04.md`
- BL-072 T1.1 closure entry: `reports/docs-architect/BACKLOG.md`
- BL-075 new entry: `reports/docs-architect/BACKLOG.md`

## Lessons learned

### L40 — Caller-layer marker vs. real-fail classification is design, not workaround

Marina decided Q6=(a) "accept blocker", which means the service blocks
on every `not r.passed`. The caller layer (bot handlers, Celery tasks)
classifies blockers by `reason_code` to render appropriate UX —
"временно недоступно" for markers, full remediation list for real-fail.

This **separation of concerns** (service-level enforcement vs.
caller-level UX) is the proper design, not a workaround:
- Service contract stays universally strict (every blocker blocks).
- Phase 4 swaps G07 marker for real body without changing service code
  or caller logic — `is_marker_only()` will keep returning False for
  the new real-fail reason_codes; UX path automatically switches from
  "временно недоступно" to remediation rendering.
- DRY: the helper `gate_block_render` lives in `src/bot/utils/` and
  is reused across two bot handlers + the Celery task uses an inline
  `marker_codes = {...}` set without crossing a module boundary
  (handler vs task layer separation preserved).

### L41 — `TransitionBlockedError` already-defined economy

5b.7a closed channel-add hook by raising `ChannelAddDeclinedError`,
which inherits from `ForbiddenError` (HTTP 403). At the same time
Phase 3b 5b.0 defined `TransitionBlockedError(ConflictError)` (HTTP 409)
without an actual raise site — pre-emptive class authoring for a
known consumer (Phase 3c).

This pre-emptive definition saved Phase 3c from authoring the exception
class, mapping it to `error_code`, and threading it through the
`RekHarborError` global handler. Phase 3c only imports + raises.

**Pattern**: when one phase introduces an exception hierarchy, define
all known consumers' classes in the same commit even if they're not
yet raised. The "dead" entries cost ~10 lines and unblock the consumer
phase from worrying about FastAPI handler wiring.

### L42 — `bypass_gates` flag location: signature vs. caller-side decoration

Considered alternatives at signature design time:
1. Caller-decorator (e.g., `with bypass_gates(): await transition(...)`).
2. Service constructor flag (`PlacementTransitionService(session, bypass=True)`).
3. **Method keyword-only parameter** (chosen).

Method parameter wins because:
- Discoverable in service signature; type checker flags incorrect usage.
- Caller decision lives at the call site, not at construction time —
  same service instance can transition some placements with bypass,
  others without (admin tooling that mixes test + production data).
- Default `False` makes enforcement opt-OUT, never opt-IN (security default).
- `transition_admin_override` is the universal admin carve-out — bypass
  on `transition()` is reserved for narrow test/QA contexts only.

## Deferred to production launch

Items consolidated for tracking, NOT part of 3c.1 scope:

- **G07 real body landing (T1.6)**: until Phase 4 ships, every
  `pending_payment` transition blocks. Production placements
  effectively halted until then.
- **G15 / G16 real bodies (T1.7, T1.8)**: payout-side; depend on
  ContractAct table + КЭП verification.
- **G17 / G18 real bodies (T1.4, T1.5)**: payout-side ORD reporting +
  VAT obligation.
- **`pending_gate_resolutions` JSONB persistence**: Phase 3d UI may
  require for async-resolution flows; not currently planned.
- **BL-075 (G01-G06 expansion in `_TRANSITION_GATES`)**: separate future
  sub-block. Marina decision required on (gate, transition) mapping.
- **81 pre-existing test failures (T1.2)**: independent workstream.

🔍 Verified against: `64a0043` (develop) | `075637a` (3c.1.1) | `e71a676` (3c.1.2) | 📅 2026-05-04
