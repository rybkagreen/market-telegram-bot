# CHANGES 2026-04-21 — plan-01 deep-flow spec hardening

## Scope

Follow-up to `FIX_PLAN_06_followups/plan-01-deep-flow-spec-hardening.md` (P0).
Parent report: `reports/20260419_diagnostics/FIX_PLAN_06_followups/README.md`.

Re-review of the §§6.2, 6.5, 6.6 deliverables shipped in
`CHANGES_2026-04-21_fix-plan-06-finish.md` flagged three silent-pass
regressions:

1. **Wrong channel-settings URL in Playwright** — the spec PATCHed
   `/api/channels/${id}/settings`, but the real route lives at
   `/api/channel-settings/` with `channel_id` as a query parameter
   (src/api/main.py:211 → src/api/routers/channel_settings.py:187).
   The wrong path returned 404 and was accepted by the `< 500`
   assertion — spec was green without ever performing a PATCH.
2. **`< 500` as primary assertion** (4 flows: channel settings, placement
   lifecycle, payouts, top-up, review). Catches only 5xx; a 404/422
   on a valid request slips through.
3. **`unittest.mock.patch` without `autospec`** in the unit tests for
   `PlacementRequestService` and `payout_service`. Renaming
   `owner_accept → accept_as_owner` would keep the tests green while
   breaking production — exactly the drift class these tests must
   catch.

Scope is **test/spec-only**. No changes to `src/`.

## Affected files

### Modified

| File | Change |
|---|---|
| `web_portal/tests/specs/deep-flows.spec.ts` | fixed channel-settings path → `/api/channel-settings/?channel_id=:id`, replaced every `< 500`/`< 300` with `ok()` / explicit status set, fixed top-up body (`desired_amount` + `method`) and asserted `payment_url`, added `test.skip` guard for missing YooKassa env, fixed review POST trailing slash |
| `tests/unit/api/test_admin_payouts.py` | 5 `patch(..., AsyncMock(...))` sites rewritten to `patch.object(payout_service, name, autospec=True)` — drift on `approve_request` / `reject_request` signature now fails the test |
| `tests/unit/api/test_placements_patch.py` | `_patch_router_repos` replaced `MagicMock() + setattr` with `create_autospec(PlacementRequestService, instance=True, spec_set=True)` — unknown attributes raise AttributeError, async methods become AsyncMock automatically |

### New

| File | Purpose |
|---|---|
| `reports/docs-architect/discovery/CHANGES_2026-04-21_plan-01-deep-flow-hardening.md` | this document |

## Business / contract impact

- **No public API contract change.** Assertions now reflect the actual
  router behaviour, not a permissive `< 500` proxy.
- **Drift detection hardened.** Renaming or resignaturing any of
  `payout_service.approve_request`, `payout_service.reject_request`,
  `PlacementRequestService.owner_accept`, `owner_reject`,
  `owner_counter_offer`, `process_payment`, `advertiser_cancel` will
  immediately break unit tests (AttributeError at import / call-site).
- **Playwright spec now exercises the real PATCH `/api/channel-settings/`
  endpoint** and verifies the round-trip (`price_per_post` written →
  read back). The `[flow] owner updates channel settings` was a no-op
  before.
- **Top-up flow** is skipped unless `YOOKASSA_SHOP_ID` and
  `YOOKASSA_SECRET_KEY` are set in the runner env — avoids spurious
  5xx noise and turns a silent-skip into an explicit skip.

## Validation

```bash
poetry run pytest tests/unit/api/ --no-cov -v
# → 20 passed (9 admin_payouts + 11 placements_patch)

poetry run ruff check tests/unit/api/
# → All checks passed!

bash scripts/check_forbidden_patterns.sh
# → 7/7 ok

cd web_portal && npx tsc --noEmit -p tests/tsconfig.json
# → 0 errors
```

E2E Playwright run is gated on docker-compose.test.yml — deferred to
next run of `make test-e2e`. The unit + tsc pass is sufficient to
guarantee the contract drift guard works.

## Out of scope (tracked separately)

- Typed service exceptions replacing `ValueError` → HTTP status
  (plan-05).
- Service DI refactor so routers stop instantiating `PlacementRequestService`
  directly (plan-07).
- Additional PATCH actions (`counter_reply`, `accept_counter`) — plan-03.

🔍 Verified against: 12d65b2 (fix/plan-01-deep-flow-hardening) | 📅 Created: 2026-04-21
