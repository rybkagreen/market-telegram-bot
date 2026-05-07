# T1.2.7 — Counter-offer flow API drift cleanup

**Branch:** feature/t1-2-test-failures-cleanup
**Started:** 2026-05-07 (nightrun)
**Pre-state HEAD:** 002e7fb (T1.2.6 commit 5)
**Pre-state baseline:** 6F / 987P / 3S / 0E + 7 lint / 0 fmt / 4 mypy
**Status:** in-progress

## Marina decision

Default — agent autonomy для simple API drift fixes (rename / move).
STOP triggers для architectural changes (removal без replacement, deep
refactor).

## Scope

2 failing tests, all `AttributeError: 'PlacementRequestRepository' object has no attribute 'counter_offer'`:

- `tests/test_counter_offer_flow.py::TestCounterOfferServiceFix1::test_advertiser_accept_counter_sets_final_price`
- `tests/test_counter_offer_flow.py::TestCounterOfferServiceFix1::test_advertiser_accept_counter_sets_final_schedule`

## Commits

### Commit 1 — `docs(t1.2.7): create placeholder CHANGES для interleaved updates`
- Hash: <set during commit>

### Commit 2 — `test(counter-offer): retire deleted repo helper, add legal-gate bypass`
- Hash: <set during commit>
- Files: `tests/test_counter_offer_flow.py::TestCounterOfferServiceFix1` (×2 tests).
- Probe: `tmp/t1_2_7_probe.md` — classified scenario (ii) per nightrun decision matrix (method moved/replaced).

#### Change 1: replace `repo.counter_offer(...)` setup with `service.owner_counter_offer(...)`

`PlacementRequestRepository.counter_offer` was deleted в commit
`daf5146 db+core+api+tasks: delete 6 placement_repo mutation helpers`
(Phase 2 § 2.B.2a) — repo became read-only per Phase 2 § 2.B.0
Decision 2. Tests' setup использовал deleted helper.

Replacement: `PlacementRequestService.owner_counter_offer(placement_id, owner_id, proposed_price, proposed_schedule)` (`src/core/services/placement_request_service.py:465-531`) — canonical state machine path, identical effect (sets counter_price/counter_schedule, transitions к counter_offer).

Side effect: dropped `comment="..."` kwarg (production method не supports — tests не assert on comment).

#### Change 2: monkeypatch `LegalComplianceService.check_gates_for_transition`

After fix 1, второй failure surfaced: `TransitionBlockedError: counter_offer -> pending_payment blocked by 1 gate(s)` (G07_SUPPLEMENTARY_AGREEMENT_SIGNED).

Root cause: Phase 3c.1 (commit 2026-05-04) added transition-time legal-compliance gate enforcement. Production `advertiser_accept_counter` does not pass `bypass_gates=True` (correct production behavior — legal compliance enforced). Unit tests pre-existed the gates и cannot satisfy G07 without legal-compliance scaffolding (Contract / SupplementaryAgreement records).

Fix: monkeypatch.setattr `LegalComplianceService.check_gates_for_transition` к return `[]` (no gate evaluations). Test scope: service price/schedule logic, NOT legal compliance flow. Bypass via test fixture, not production change.

#### Closes 2F. Pre-state: 6F/987P. Expected post-state: 4F/989P.

- Verify: `pytest TestCounterOfferServiceFix1 -v` → 2 PASSED. Lint clean. Format applied (lines wrapping).
