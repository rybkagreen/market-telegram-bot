# Phase 3a Foundation — Closure (Blocks 1, 1.5, 2, 3, 4)

**Date**: 2026-05-02
**Branch**: feature/legal-compliance-gates
**Status**: Phase 3a Foundation complete; ready for Marina's merge-timing decision
**Commits ahead of develop**: 18

## Summary

Bundles all Phase 3a Foundation work — schema scaffolding, service plumbing,
S-48 cleanup, and S-48 taxonomy clarification. Blocks 1, 1.5, 2, 3, 4 are
now closed. No business logic shipped; all gate-checker bodies, transition
tables, and provider implementations remain `NotImplementedError` Phase 3b
stubs.

This single CHANGES file is an **additive overview** atop per-block CHANGES
files (preserved as-is per CLAUDE.md append-only rule).

## Per-block CHANGES files (preserved)

- `CHANGES_2026-05-02_phase3a-block1-foundation.md`
- `CHANGES_2026-05-02_phase3a-72h-correction.md` (Block 1.5)
- `CHANGES_2026-05-02_phase3a-block2-skeleton.md`
- `CHANGES_2026-05-02_phase3a-block3-cleanup.md`
- `CHANGES_2026-05-02_clarify-s48-patterns.md` (chore branch, merged into develop pre-Block-3)
- `CHANGES_2026-05-02_phase3a-foundation-closure.md` (this file)

## Phase 3a deliverables (all blocks combined)

### Schema (Block 1)

9 columns added across 4 tables in `0001_initial_schema.py` (pre-prod schema
edit, not migration):

- `legal_profile`: `fns_verification_status`, `fns_last_checked_at`, `egrul_egrip_snapshot`, `egrul_snapshot_at`
- `payout_request`: `payout_method_type`
- `placement_request`: `gate_results_snapshot`, `last_gate_check_at`
- `ord_registration`: `deadline_at`, `last_ord_check_at`

### Enums + schemas (Block 1)

- `PlacementGate` enum (18 values, G03=`LEGAL_STATUS_COMPLIANT` post-1.5 correction)
- `GateResult` dataclass + `GateResultResponse` Pydantic schema
- Snapshot test fixture

### 72h drift correction (Block 1.5)

Plan claim "72h ORD deadline per ФЗ-38" was empirically falsified — real
deadline = end of month following publication month per ФЗ-38 ст. 18.1 +
ПП-1427. ERRATUM applied to plan + 3 research artifacts + 3 schema/code
comments. `deadline_at` column concept valid; value formula correction
deferred to Phase 3b.

### Service plumbing (Block 2)

- 2 custom exceptions (`TransitionBlockedError`, `ChannelAddDeclinedError`)
  in `src/core/exceptions.py`
- 4 repo methods (`ContractRepo.has_signed_framework`, `LegalProfileRepo.get_verification_status`, `PayoutRepository.get_valid_for_owner`, `UserRepository.get_with_legal_profile`)
- 6 gate-checker module skeletons under `src/core/services/gates/` (18 `NotImplementedError` stubs total)
- `LegalComplianceService` skeleton with real dispatch via `_GATE_CHECKERS` registry; `gates_for_transition` and gate bodies = Phase 3b stubs

### S-48 cleanup + taxonomy (chore branch + Block 3 + Block 4)

- CLAUDE.md S-48 section restructured to name three canonical patterns:
  - Pattern 1 — Caller-owns (default, no marker)
  - Pattern 2 — Self-contained (marker: `# S-48: self-contained pattern`)
  - Pattern 3 — External-boundary (marker: `# S-48: external-boundary (<reason>)`)
- 4 carve-out markers applied (badge_service × 3 = Pattern 2; publication_service × 1 = Pattern 3)
- 5 audit log integrations (LegalProfileService × 3 + PayoutService × 2) using existing `AuditLogRepo`
- 6 router redundancy removals (contracts.py × 3 + channels.py × 1 simple + 2 commit→flush refactors at lines 1139, 1191)
- 1 router refactor at channels.py:423 (commit→flush, preserve 409 UX)
- After Block 4: `channels.py` contains **zero** `session.commit()` calls

### Plan + research artifacts (research dispatched 2026-05-02)

4 parallel Explore agents (A: legal_profile, B: scattered checks, C: payout+bot audit, D: external integrations) + consolidated artifact `PHASE3_RESEARCH_2026-05-02.md` with decision sheet, roadmap, 4-sprint split.

## Verification

| Gate | Pre-Phase-3a baseline (v0.2.0 + post-prep) | Phase 3a Foundation result |
|---|---|---|
| ruff (`src/`) | 4 | 4 |
| mypy (`src/`) | 10 | 10 |
| pytest unit (excl. test_main_menu) | 62 fail / 496 pass / 558 collected | 62 fail / 496 pass / 558 collected |
| Snapshot `gate_result_response.json` | n/a (added in Block 1) | matches |
| Snapshot `tests/unit/test_contract_schemas.py` | 23 pass | 23 pass |
| alembic head | `e6a88faa9fa0` | `e6a88faa9fa0` |
| tsc (mini_app + web_portal) | clean | clean |

**Zero regressions** vs v0.2.0 baseline.

## Lessons from Phase 3a Foundation

Surfaced for Phase 3 closure batch (NOT BACKLOG entries yet — accumulating):

- **L8** — Regulatory fact-claim verification protocol. Plan citations must trace to primary source before propagating; "per <law>" suffix reads downstream as citation, not paraphrase.
- **L9** — BL number references in promtах must be grep-verified, not memory-predicted.
- **L10** — Per-block CHANGES vs Block-N-bundle drift under hook pressure. Hook can override planner decision; either accept (default) or make hook-resistance explicit.
- **L11** — HEAD drift acknowledgment in agent reports. Promtах must explicitly accept "newer HEAD if substantively unchanged".
- **L12** — Grep-only S-48 classification false positives. Verify session ownership before classifying. **Codified** in CLAUDE.md by chore/clarify-s48-patterns.
- **L13** — Pattern-based discovery, not line-based. 3 of 7 router sites in Block 3 used the same `try/except IntegrityError → 409` pattern, but only :423 was flagged. Pattern-based grep would have caught all three at once. **Deferred** to Phase 3 closure batch (Marina decision Q2=(b)).

## Architectural debt accumulated (Phase 3 closure batch)

- L8-L13 codification (above)
- ORD `_global_provider` module-state pattern — refactor with centralized provider registry
- `OrdRegistrationResult` dataclass dead code (`ord_provider.py`)
- Verification drift — `PROJECT_KNOWLEDGE_v3.md` + `PII_AUDIT_2026-04-28.md` phantom references; `PlacementStatus` location mismatch (plan vs code); `PayoutMethodRepository` non-existence
- Dispute-72h independence audit — verify not tied to unverified source
- Orphan CSS files — `OwnPayoutRequest.module.css`, `LegalProfileView.module.css`
- mypy line drift in CLAUDE.md — claimed 529 errors, actual 10
- CHANGELOG hook noise on feature branches — branch-aware fix candidate
- Pydantic ValidationError input_value disclosure — env values leak in startup logs
- `payout_method_type` column = varchar(16); Marina decision D2 was enum + per-method validators — Phase 3b territory
- `tests/unit/test_placement_transition_service.py` is 0 bytes (pre-existing, surface only)
- (M) candidate — architectural fitness test for S-48 patterns

## What remains in Phase 3

| Sub-phase | Scope | Estimate |
|---|---|---|
| Phase 3b | Gate-checker logic (18 stubs → real); Yandex provider real; transition→gates table | 15-20h, multi-session |
| Phase 3c | Integration into PlacementTransitionService + channel-add hook | TBD |
| Phase 3d | API endpoint exposure | TBD |
| Phase 3 closure | BACKLOG batch commit (L8-L13 + architectural debt above) | 1-2 sessions |

## Out of scope (deferred from Block 4)

- L13 codification in CLAUDE.md auditing guidance — Phase 3 closure batch
- (M) Architectural fitness test — post-Phase-3 investment
- Tests for any Block 1-4 code — Phase 3b (paired with logic)
- BACKLOG.md updates — Phase 3 closure batch

## Commit ledger (Phase 3a Foundation, by block)

### Pre-Block-1 (chore + prep, on develop)

| Commit | Hash | Description |
|---|---|---|
| Restore OwnPayoutRequest.tsx | `90616d7` | 16.3 deeplink target placeholder |
| Plan terminology align | `d51d62c` | legal_type → legal_status in plan § 3 |
| chore/clarify-s48-patterns | `9dc24ec` (merge `08e2fd2`) | S-48 three-pattern taxonomy |

### feature/legal-compliance-gates branch

| Block | Commits | Hashes |
|---|---|---|
| 1 — Schema foundation | 2 + 1 docs | `5ab1651`, `9556b49`, `f3f16e4` |
| 1.5 — 72h correction | 1 | `1921e59` |
| Housekeeping | 1 | `82bc0fe` (research artifacts A+C) |
| 2 — Service plumbing | 4 + 1 docs | `1481717`, `46f6465`, `e0339f6`, `25d2997`, `905da11` |
| Merge develop (chore + prep) | 1 | `f294d4a` |
| 3 — Cleanup | 4 + 1 docs | `1645a64`, `4eff829`, `11c3c5f`, `2f7c3d0`, `d3cbaf0` |
| 4 — Closure | 2 | `46d9eed` (4.1), this commit (4.2) |

Final HEAD: <fill in after commit>
Final commits ahead of develop: 18

## Notes

Phase 3a Foundation hit two genuine surprises mid-flight (72h drift, S-48
caller audit) and one mid-block discovery (L13). Each was caught by
empirical verification before mutation, surfaced as a lesson, and resolved
without rollback. Branch history is linear and intact; no force-pushes.

🔍 Verified against: `46d9eed` (HEAD before this commit) | 📅 Updated: 2026-05-02
