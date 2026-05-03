# Phase 3b 5b.4 — Owner gate bodies G04-G05 + G06 Phase 5 marker

**Date**: 2026-05-02
**Branch**: feature/phase3b-compliance-gates
**Commits**: 5b.4.1 → 5b.4.3 (2 code + 1 docs)
**Origin**: Symmetric mirror of 5b.3 advertiser pattern; G06 migrated from Foundation stub to Phase 5 pending marker.

## Scope

| Gate | Status | Approach |
|---|---|---|
| G04 | Real | Mirror G01: reads `User.legal_status_completed` for `placement.owner_id` |
| G05 | Real | Mirror G02: `ContractRepo.has_signed_framework` with `role="owner"` |
| G06 | Phase 5 marker | NotImplementedError → `GateResult(passed=False, blocker=True, PHASE5_PENDING)` |

## Files modified

- `src/core/services/gates/owner_gates.py` — replaced 3 stub bodies (G04 + G05 real; G06 marker)
- `tests/unit/test_owner_gates.py` (NEW) — 10 cases (5 G04 + 3 G05 + 2 G06)
- `CHANGELOG.md` — Unreleased section appended
- `reports/docs-architect/discovery/CHANGES_2026-05-02_phase3b-5b4-owner-gates.md` (NEW — this file)

## Commits

| # | Hash | Title |
|---|---|---|
| 5b.4.1 | `51f4401` | feat(gates): G04 + G05 owner-side bodies + tests |
| 5b.4.2 | `07ab5f3` | feat(gates): G06 Phase 5 marker |
| 5b.4.3 | (this commit) | docs(phase3b): 5b.4 closure — owner gate bodies |

## Phase A+B+C trace

Phase A+B artifact: `tmp/PHASE3B_5B4_OWNER_GATES_INVESTIGATION_2026-05-02.md`. Owner-specific findings:

- **A.2 — Owner identity path:** `PlacementRequest.owner_id` is a direct FK column to `users.id` (line 73-75), parallel to `advertiser_id`. No Channel detour required. Owner gate bodies use `placement.owner_id` exactly mirroring `placement.advertiser_id`.
- **A.3 — ChannelRepo state:** Not needed per A.2; no new repo method shipped in 5b.4. (`telegram_chat_repo.py` exists for 5b.7 channel-add hook to consume separately.)
- **A.5 — `ContractRepo.has_signed_framework`:** accepts `role="owner"` as first-class supported value. `Contract.role` column carries owner-vs-advertiser discriminator. The hardcoded `contract_type="advertiser_framework"` umbrella name (L18 deferral) applies to both roles unchanged from 5b.3.
- **A.6 — Existing scaffolding:** 3 Foundation Block 2 NotImplementedError stubs in `owner_gates.py` (36 LOC); none mutated since.
- **A.8 — G06 marker design:** option (b) selected — `GateResult(passed=False, blocker=True, PHASE5_PENDING)`. Option (a) `NotImplementedError` would block 5b.7 channel-add integration; option (c) `passed=True` would silently false-pass post-Phase-5. Option (b) is honest about the phase boundary and lets channel-add land end-to-end.
- **A.9 — `GateReason` enum:** zero new entries needed. 5b.3 already declared `PHASE5_PENDING` (line 19) speculatively; 5b.4 G06 marker consumes it.

**B.5 Marina decisions required: 0.** Phase A+B+C ran fully autonomously per scope guards.

## Test coverage

`tests/unit/test_owner_gates.py` — 10 cases:

- **G04 (5):** `user_not_found_returns_blocker`, `legal_profile_missing_returns_blocker`, `legal_profile_incomplete_returns_blocker`, `complete_returns_pass`, `remediation_url_points_to_legal_profile`
- **G05 (3):** `unsigned_returns_blocker`, `signed_returns_pass`, `calls_repo_with_owner_role` (verifies `role="owner"` literal in repo call)
- **G06 (2):** `returns_phase5_marker` (shape: G06 enum, passed=False, blocker=True, PHASE5_PENDING, no remediation), `does_not_call_repos` (no `session.execute` / `commit` / `flush` interactions)

Reuses 5b.3 `_fake_user` / `_fake_legal_profile` helpers verbatim. Placement fixture diff: `owner_id=42` instead of `advertiser_id=42`.

## Verification

| Gate | Pre-5b.4 baseline | 5b.4 result |
|---|---|---|
| ruff (`src/`) | 4 | 4 |
| mypy (`src/`) | 10 | 10 |
| pytest unit (excl. test_main_menu) | 62 fail / 548 pass / 610 collected | 62 fail / 558 pass / 620 collected (+10) |
| Snapshot tests (`test_contract_schemas.py`) | 23 pass | 23 pass |
| Alembic head | `e6a88faa9fa0` | `e6a88faa9fa0` |
| S-48: no new commit/flush/rollback in `gates/` | yes | yes (0) |
| Smoke import (`from src.core.services.gates import owner_gates`) | OK | OK |

## Out of scope (deferred)

- **Phase 5 G06 body** (M4 + M6 — payout method matrix + tax receipts):
  - `bank_card`: YooKassa Payouts recipient-check
  - `sbp`: SBP bank selector + recipient-check
  - `bank_transfer`: BIK + corresponding-account validation (IE/LE)
- **5b.7 channel-add hook integration** — Phase A.8 confirms G06 marker semantics designed to support it; 5b.7 territory.
- **5b.5+ transition service integration** — `TransitionBlockedError` raise path; 5b.5+ territory.
- **L18 contract_type rename** (`"advertiser_framework"` → role-neutral `"framework"`) — Phase 3 closure batch unchanged.
- **S1 `Contract.expires_at` semantics** — no expiry policy yet; Phase 4+ renewal flow territory.

## Notes

5b.4 reused 5b.3 precedents fully:
- `GateReason` enum (no new entries needed)
- `portal_routes` constants (no additions)
- Pure mocked unit test pattern (`MagicMock(spec=AsyncSession)` + `monkeypatch` on repo classes)
- Direct repo imports (`UserRepository`, `ContractRepo`)
- Pattern 1 S-48 contract throughout

Owner identity resolution via `placement.owner_id` direct FK is the cleanest possible mirror of advertiser pattern. Sets a precedent for 5b.7 channel-add to use a separate Channel-by-id load path (since channel-add gate evaluation works with a `Channel` aggregate, not a `PlacementRequest`).

🔍 Verified against: `07ab5f3c1bcfcddc61d755b40a9070afb529d574` | 📅 Updated: 2026-05-02T00:00:00Z
