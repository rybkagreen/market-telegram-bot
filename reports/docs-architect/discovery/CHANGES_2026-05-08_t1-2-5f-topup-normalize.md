# T1.2.5f — Topup normalize (Bundle D)

**Branch:** feature/t1-2-5f-topup-normalize
**Started:** 2026-05-08
**Pre-state HEAD:** bb6623b (develop merge base)
**Pre-state baseline:** 0F / 993P / 3S / 0E + 7 lint (conftest) / 0 format / 4 mypy (mediakit)
**Post-state HEAD:** 58a1dd0
**Post-state baseline:** 0F / 997P / 3S / 0E + 7 lint (conftest) / 0 format / 4 mypy (mediakit)
**Status:** closed

## Marina decision: Bundle D

Hybrid — placeholder mini_app (LegalProfileView pattern) + full backend pin (BL-046 mirror) + adapted bot regression. Apply payout deeplink pattern (BL-055 / 16.3) к topup flow.

Per-decision summary: see PROMPT_T1_2_5f_PHASE_C.md.

Side-fix α: orphan OwnPayoutRequest.module.css deletion (T1.2.5e leak).
Side-fix β: topup:amount:custom Decimal cast — DEFERRED к BACKLOG.

## Commits

### Commit 1 — `docs(t1.2.5f): create placeholder CHANGES для interleaved updates`
- Hash: fcaf9e6
- Files: reports/docs-architect/discovery/CHANGES_2026-05-08_t1-2-5f-topup-normalize.md (NEW)

### Commit 2 — `feat(billing): pin topup endpoints к web_portal audience + whitelist /topup`
- Hash: c6b5423
- Files (3): src/api/routers/billing.py, src/config/settings.py, tests/unit/api/test_pii_audience_pinning.py
- Decisions: 4.a + 5.a + 7.a partial (PII pinning tests).
- POST /api/billing/topup и GET /api/billing/topup/{payment_id}/status pinned к get_current_user_from_web_portal.
- bot_portal_exchange_allowed_paths default tuple gains "/topup".
- 4 PII pinning tests added (TestTopupRejectsMiniAppJwt × 2 + TestWebPortalJwtPassesAudienceGate × 2).

### Commit 3 — `refactor(bot): delete TopupStates + 4 handlers + keyboards file; add TestNoBotTopupFlow`
- Hash: ec65993
- Files (6): bot handlers + keyboards + states + tests.
- Decisions: 2.iii.b + 2.iv.a + 2.v.a + 6.b adapted.
- Removed: src/bot/keyboards/billing/topup.py (entire file), 4 topup_*. handlers from billing.py, TopupStates class + __init__.py export, tests/integration/test_bot_topup_handler.py.
- Refactored: topup_start handler → redirect-only stub.
- Added: TestNoBotTopupFlow (3 assertions).

### Commit 4 — `feat(bot): cabinet + insufficient-funds inline URL deeplinks для topup`
- Hash: c2983b7
- Files (5): cabinet keyboard + handler + 3 insufficient-funds callsites.
- Decisions: 2.i.a + 2.ii.a.
- cabinet_kb gains topup_url kwarg (mirror payout_url pattern).
- 3 insufficient-funds callsites converted к URL buttons (billing.buy_plan, placement.placement_payment, camp_payment_kb).

### Commit 5 — `chore(mini_app): replace TopUp с placeholder + delete TopUpConfirm/api/hooks/types`
- Hash: 58a1dd0
- Files (9): TopUp.tsx (placeholder), 4 deletions, 4 modifications.
- Decisions: 3.i.a + 3.ii.c + 3.iv.c + 3.v.a + 3.vi.a + 3.vii.a + side-fix α.
- TopUp.tsx replaced с placeholder containing OpenInWebPortal к "/topup".
- Deleted: TopUpConfirm.tsx, TopUp.module.css, TopUpConfirm.module.css, /topup/confirm route, createTopUp/getTopUpStatus functions, useCreateTopUp/useTopUpStatus hooks, TopUpRequest/TopUpResponse types.
- Side-fix α: deleted orphan mini_app/src/screens/owner/OwnPayoutRequest.module.css (T1.2.5e leak).

### Commit 6 — `docs(t1.2.5f): closure CHANGES finalize + tmp cleanup`
- Hash: <set during commit>
- Finalizes CHANGES with post-state baseline + verification footer + deferred entries.
- Cleans up tmp/t1_2_5f_*.md probe files (4 files) per post-Phase-C policy.

## Test count delta vs pre-Phase-C baseline (993P)

- +4 PII pinning tests (Commit 2)
- +3 TestNoBotTopupFlow tests (Commit 3)
- −2 deleted test_bot_topup_handler.py (Commit 3)
- −1 deleted test_topup_states_defined (Commit 3)
- Net: +4 — matches actual 997P (993 + 4).

Note: PROMPT_T1_2_5f_PHASE_C.md stated expected 996P after Commit 3. The
prompt's accompanying calculation (+3, −2, −1 from 997P) actually gives 997P;
"996" was a single-digit miscount. Actual 997P matches prompt's listed deltas.

## Deferred to production launch

- **Side-fix β: `topup:amount:custom` literal-string Decimal cast** — input validation thinness. Originally at the now-deleted `topup_select_amount` handler in `src/bot/handlers/billing/billing.py`. Web portal `/topup` flow is authoritative, so risk is contained to web_portal validation. If a similar pattern lands elsewhere in the codebase, a "input validation hardening — Decimal cast strings" BACKLOG entry should be added by the planner.

- **TopupResponse contract drift snapshot** — Decision 7.d not selected. The `TopupResponse` model in `src/api/routers/billing.py` is not currently in `tests/unit/test_contract_schemas.py` covered models. If future contract drift for topup matters, add it там.

- **Pre-fill amount support (Decisions 1.f / 5.f / 5.g)** — defer к UX improvement BACKLOG. Single-target `/topup` was selected (Decision 1.e). The user clicks the deeplink and sees the web-portal topup form without a pre-filled amount. If users complain about typing the amount twice, a query-string-based pre-fill flow (e.g. `/topup?amount=1000`) can be added; the whitelist parser tolerates query params today.

## Verification footer

🔍 Verified against: 58a1dd0 | 📅 Updated: 2026-05-08T10:32:04+03:00
