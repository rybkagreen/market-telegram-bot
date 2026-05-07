# T1.2.5e — Payout cleanup + dead-code purge + pre-test gates

**Branch:** feature/t1-2-test-failures-cleanup
**Started:** 2026-05-07
**Pre-state HEAD:** b7d4589
**Pre-state baseline:** 12F / 997P / 5S / 0E + 21 lint / 14 format / 10 mypy
**Status:** in-progress (commit 8 finalizes)

## Marina decisions

- **Q1-frame=(c)+(d):** full backend dead-code purge (PayoutService methods + PayoutComplianceService skeleton + free function `calculate_payout`) + topup normalize deferred к T1.2.5f.
- **Q2-frame=(a):** delete bot admin payout `approve_payout` / `reject_payout` callbacks; "Выплаты" admin menu button preserved (live `show_pending_payouts` target).
- **Q4-frame=(a):** pre-test gates fix included в this sub-block.
- **Q1-Phase-C=(a):** conftest 7 lint errors accepted as known residual (BL-024 prohibits touching `tests/unit/conftest.py`).
- **Q2-Phase-C=(c):** mediakit_service.py 4 typecheck errors deferred к BACKLOG (orthogonal architectural cleanup).
- **Q3-Phase-C=(b):** commit 7 split в 7a (lint), 7b (format), 7c (typecheck) для cleaner history.

## Commits

### Commit 1 — `refactor(bot): delete empty admin payout approve/reject callbacks`
- **Hash:** c9d3175
- **Files:** `src/bot/handlers/admin/users.py` (-12 lines)
- **Verify:** 12F / 997P / 5S / 0E (+ unchanged 21 lint / 14 format / 10 mypy)
- **Note:** First gate run showed 13F due к flake `tests/unit/test_content_filter.py::test_check_case_insensitive` (Mistral non-determinism, `0.25 == 1.0`). Re-run confirmed 12F restoration. Flake unrelated к commit diff.

### Commit 2 — TBD (mini_app payout removal)

### Commit 3 — TBD (stale bot comment update)

### Commit 4 — TBD (PayoutService dead methods)

### Commit 5 — TBD (PayoutComplianceService skeleton)

### Commit 6 — TBD (free function `calculate_payout`)

### Commit 7a — TBD (lint cleanup)

### Commit 7b — TBD (format cleanup)

### Commit 7c — TBD (typecheck cleanup)

### Commit 8 — TBD (closure docs + tmp cleanup)

## Deferred to production launch

(filled by commit 8 finalizer)

## Verification footer

(filled by commit 8 finalizer)
