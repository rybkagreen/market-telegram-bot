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

### Commit N — TBD

## Deferred to production launch

(filled by closure)

## Verification footer

(filled by closure)
