# CHANGES 2026-04-21 — plan-03 placement PATCH coverage completion

## Scope

Follow-up to `FIX_PLAN_06_followups/plan-03-placement-patch-coverage-completion.md`
(P1). Closes the gaps in `tests/unit/api/test_placements_patch.py`
left after FIX_PLAN_06 §6.6:

1. **2 of 7 PATCH actions had no tests** — `accept-counter` and
   `counter-reply` (the latter is the FIX #20 / S-45 mechanism that
   broke the counter-offer deadlock; precisely the area where past
   regressions happened).
2. **`session.rollback()` was never asserted.** The router's three
   error branches (`HTTPException`, `ValueError → 409`,
   `Exception → 500`) all call `session.rollback()` (placements.py:
   549–563), but every previous test mocked the service with
   `return_value=…` and never exercised the failure paths — the
   rollback branch was effectively dead code from the test
   perspective. Missing rollback was the root cause of ESCROW-002.
3. **`reason_code` fallback** (placements.py:58) was uncovered.
4. **Channel-not-found → 404** (placements.py:502) was uncovered.

Test-only sprint. No `src/` changes.

## Affected files

### Modified

| File | Change |
|---|---|
| `tests/unit/api/test_placements_patch.py` | +11 tests (5 new classes), +`session_spy` / `client_as_owner_with_spy` / `client_as_advertiser_with_spy` fixtures |

### New

| File | Purpose |
|---|---|
| `reports/docs-architect/discovery/CHANGES_2026-04-21_plan-03-placement-patch-coverage.md` | this document |

## New test inventory

| Class | Tests | Covers |
|---|---:|---|
| `TestPatchAcceptCounter` | 3 | happy path (counter_offer → pending_payment), 409 wrong status, 403 owner-not-advertiser |
| `TestPatchCounterReply` | 3 | happy path with price+comment (4-arg autospec match), 400 missing price, 403 owner-not-advertiser |
| `TestPatchRejectReasonCode` | 1 | router falls back to `reason_code` when `reason_text` is absent |
| `TestChannelNotFound` | 1 | placement exists but channel was deleted → 404 |
| `TestErrorPathsCallRollback` | 3 | `ValueError → 409 + rollback`, `HTTPException → rollback + re-raise`, `RuntimeError → 500 + rollback`. Every test asserts `session.commit` was NOT awaited. |

Total: 11 new tests. With 11 pre-existing → **22 unit tests** for
unified PATCH.

## Why the rollback assertions matter

ESCROW-002 (closed 2026-04-21) was caused by a missing rollback in a
financial code path: the transaction stayed open across an exception,
poisoning the next request and silently committing partial state.
The unit tests in this file mocked the service so cleanly that the
exception branches were unreachable — the regression class would have
re-emerged invisibly.

The new `session_spy` fixture closes that gap: each error-path test
exercises a real `raise` from the mocked service (autospec'd
`PlacementRequestService.owner_accept` / `owner_counter_offer` with
`side_effect=…`) and asserts both
`session.rollback.assert_awaited_once()` and
`session.commit.assert_not_awaited()`.

Together with the autospec drift-guard from plan-01, the unified
PATCH is now boxed in on both sides: a method rename breaks the
test (autospec), and a missing rollback breaks the test (spy).

## `_action_counter_reply` signature note

Router calls `service.advertiser_counter_offer(placement_id, user_id,
Decimal(str(price)), comment)` — four positional arguments, with
`comment=None` passed even when missing from the body
(placements.py:134–136). The autospec'd mock therefore expects a
4-tuple in `assert_awaited_once_with(...)`. Future refactors that
shift `comment` to a keyword-only or default argument will break
this assertion — captured intentionally.

## Validation

```bash
poetry run pytest tests/unit/api/test_placements_patch.py --no-cov -v
# → 22 passed in 3.24s

poetry run ruff check tests/unit/api/
# → All checks passed!

bash scripts/check_forbidden_patterns.sh
# → 7/7 ok
```

## Out of scope (tracked separately)

- Service-level tests for `advertiser_accept_counter` /
  `advertiser_counter_offer` business logic — already covered in
  `tests/test_counter_offer_flow.py` (integration).
- Typed exception hierarchy replacing `ValueError → 409` mapping —
  plan-05.
- Service DI refactor so the router stops instantiating
  `PlacementRequestService` directly — plan-07.

🔍 Verified against: 7c15f56 (main) | 📅 Created: 2026-04-21
