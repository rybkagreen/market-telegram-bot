# Phase 3b 5b.3 — Advertiser gate bodies G01-G03

**Date**: 2026-05-02
**Branch**: feature/phase3b-compliance-gates
**Commits**: 5b.3.1 → 5b.3.4 (3 code + 1 docs)
**Origin**: First sub-block with real gate logic; sets precedent for 5b.4-5b.7.

## Scope

Three gate bodies replacing Foundation NotImplementedError stubs, plus shared infrastructure.

| Gate | Status | Approach |
|---|---|---|
| G01 | Real | Reads User.legal_status_completed flag |
| G02 | Real | ContractRepo.has_signed_framework direct call |
| G03 | Interim (5b.3 / pre-5b.8) | Checksum via validate_inn_checksum / validate_ogrn_checksum; FNS/EGRUL deferred |

## Files modified

- `src/core/enums/gate_reason.py` (NEW) — GateReason(StrEnum), 13 entries
- `src/constants/portal_routes.py` (NEW) — 3 web-portal path constants
- `src/core/services/gates/advertiser_gates.py` — replaced 3 stub bodies + private G03 helpers
- `tests/unit/test_advertiser_gates.py` (NEW) — 25 cases

## Commits

| # | Hash | Title |
|---|---|---|
| 5b.3.1 | `6ae7b7c` | feat(gates): GateReason enum + portal route constants + G01 body + tests |
| 5b.3.2 | `a592898` | feat(gates): G02 body + tests |
| 5b.3.3 | `78fe07f` | feat(gates): G03 interim body (checksum-only) + tests |
| 5b.3.4 | (this commit) | docs(phase3b): 5b.3 closure — advertiser gate bodies |

## Phase A+B → Phase C trace

Phase A+B artifact: `tmp/PHASE3B_5B3_ADVERTISER_GATES_INVESTIGATION_2026-05-02.md`. 6 design questions + 3 scope-expansion candidates surfaced; Marina sign-off resolved each:

| Item | Decision | Effect |
|---|---|---|
| Q1 | (a) G03 checksum-only + 5b.8 marker | A.8: fns_verification_status write-orphaned; (b) would block all SE; (c) blocks all advertisers post-5b.5 |
| Q2 | (c) GateReason(StrEnum) | Mirrors PlacementGate(StrEnum) pattern |
| Q3 | (a) Static web-portal paths | Bot deeplinks runtime-minted (5-min TTL); per ФЗ-152 + plan §3.D web-portal-only |
| Q4 | Pure mocked unit tests | 25 cases; integration belongs to 5b.5 (transition raise path) |
| Q5 | Defer G02 expiry | Informational; no expiry policy in code today |
| Q6 | Direct repo imports | Informational; avoids circular dep via LegalComplianceService |
| S1 | Defer Contract.expires_at | No renewal flow; revisit Phase 4+ |
| S2 | Defer Literal[...] strengthening | Phase 3 closure batch territory |
| S3 | Defer write paths for inn_checksum_valid / fns_verification_status | 5b.8 territory |

## Test coverage

`tests/unit/test_advertiser_gates.py` — 25 cases:

- G01: 5 (user not found, profile missing, profile incomplete, complete, remediation URL)
- G02: 3 (unsigned, signed, role-correct)
- G03: 15 parametrized (per-status × valid/invalid INN+OGRN+OGRNIP) + 2 informational

Pure mocked: MagicMock(spec=AsyncSession) + monkeypatch on repo classes.

INN/OGRN test fixture values verified against real `validate_inn_checksum` /
`validate_ogrn_checksum` before commit (4 valid values pass, 4 invalid fail).

## Verification

| Gate | Pre-5b.3 baseline | 5b.3 result |
|---|---|---|
| ruff (`src/`) | 4 | 4 |
| mypy (`src/`) | 10 | 10 |
| pytest unit (excl. test_main_menu) | 62 fail / 523 pass / 585 collected | 62 fail / 548 pass / 610 collected |
| Snapshot tests | 23 pass | 23 pass |
| Alembic head | `e6a88faa9fa0` | `e6a88faa9fa0` |
| S-48: no new commit/flush/rollback | yes | yes |

## Out of scope (deferred)

- 5b.8 enrichment of G03 (FNS NPD status)
- Phase 5 enrichment of G03 (EGRUL/EGRIP freshness)
- Owner gates G04-G06 (5b.4 territory)
- Transition service integration (5b.5+ territory)
- Channel-add hook (5b.7 territory)
- Phase 5 stub markers G06/G18 — deferred to 5b.10 closure
- L18 contract_type rename, L19 check_completeness side-effect split — Phase 3 closure batch

## Lessons accumulating for Phase 3 closure batch

- **L18 (new)** — Contract.contract_type hardcoded "advertiser_framework" for both advertiser and owner framework contracts. Role discriminator separate column. Functional but misleading. Closure may rename.
- **L19 (new)** — LegalProfileService.check_completeness has side effects (writes + flush). "Read" mutating state, contrary to "чистая функция" plan language. Functional in current usage. Closure may split into pure compute + write.

## Notes

5b.3 sets precedent for 5b.4-5b.7:
- StrEnum pattern for reason codes
- Constants module for remediation URLs
- Direct repo imports (no LegalComplianceService dependency)
- Pure mocked unit tests with monkeypatch on repo classes
- Phase A+B+C structure for non-trivial sub-blocks

G03 interim is NOT a stub — ships real validator rejecting junk INNs/OGRNs/OGRNIPs. 5b.8 / Phase 5 enrichment will *add* layered checks, not replace this interim logic.
