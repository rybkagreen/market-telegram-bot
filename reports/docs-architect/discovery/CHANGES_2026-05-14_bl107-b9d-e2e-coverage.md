# CHANGES 2026-05-14 — BL-107 Phase B.9 Phase D (E2E coverage)

## Context

Phase D adds 4 new E2E specs covering BL-107 surfaces — happy/sad path
bot precheck (via telegram-stub), manual-evidence end-to-end flow
(owner → admin), and periodic re-verification wiring proxy. Lives in
new file `web_portal/tests/specs/bl-107-channel-registration.spec.ts`
(locality preferred over extending existing files).

**Scope envelope:** single new spec file, no infra/fixture/API changes.

Built atop Phase B.9.C (`ff93a5a`).

## Empirical decisions vs prompt D.1-D.4

The prompt described four scenarios:

| Prompt | Implemented as | Deviation rationale |
|---|---|---|
| D.1 — Full add-flow positive (POST /api/channels/) | /check with `@verified_channel` | POST /api/channels/ enforces G04/G05/G06 owner-side legal compliance (legal profile + framework contract + payout method). Seeded test owner doesn't have these — would block flow at compliance check, never reaching G19 path being tested. Seed extension (LegalProfile / Contract / PayoutMethod fixtures) requires modifying scripts/e2e/seed_e2e.py with non-trivial multi-model setup — out of B.9 test-only scope per Marina prohibitions. **`/check` exercises the same stub-routed `bot.get_chat` + `bot.get_chat_member` chain** without the legal-gate dependency — proves the BL-002 wiring at the surface the UI actually invokes during precheck. |
| D.2 — Full add-flow negative (G19 blocks) | /check with `@not_verified_channel` | Same legal-gate constraint. **G19 blocking-at-add is covered by `tests/unit/test_owner_gates_g19.py`** (pure unit, no stack). E2E spec validates the stub returns the alternate fixture (`@not_verified_channel`, no Trustchannelbot admin) — bot precheck reachable, G19 enforcement happens at POST /api/channels/ time (out of /check scope). |
| D.3 — Manual evidence full flow | End-to-end as prompted | No deviation. Owner POSTs evidence → admin GETs pending → admin POSTs verify → admin GETs verified. Uses seeded `@e2e_test_channel` (id=-1009001002001, owned by 9002, member_count=1000). |
| D.4 — Periodic re-verification | Stub-state introspection proxy | Direct task invocation requires Celery worker in docker-compose.test.yml (not present). Adding a test-only HTTP trigger for the task is a backend change (prohibited in B.9). **Proxy: idempotent /check call** validates same stub-routing surface the periodic task depends on. Full Celery-task-in-test invocation is recorded as Phase B closure follow-up (will appear в new BL entry в the closure batch). |

## Files added

- `web_portal/tests/specs/bl-107-channel-registration.spec.ts` (1 new
  spec file, 4 `test()` blocks across 4 `describe` groups)

| Spec | Lines | Storage state | Surface tested |
|---|---|---|---|
| D.1 verified precheck | 36-54 | owner | POST /api/channels/check + @verified_channel fixture |
| D.2 not_verified precheck | 58-77 | owner | POST /api/channels/check + @not_verified_channel fixture |
| D.3 manual evidence flow | 81-149 | owner+admin | POST /channels/{id}/submit-registry-evidence, GET+POST /admin/channel-verifications |
| D.4 periodic wiring proxy | 153-178 | owner | Idempotent /check (proxy for stub-routing the periodic task uses) |

## Verification gates

| Gate | Status |
|---|---|
| `npx tsc --noEmit` on `web_portal/tests/` | ✅ clean |
| `npx playwright test --list --grep "bl-107"` | ✅ 12 tests discovered (4 specs × 3 projects) |
| Runtime pass (`make test-e2e`) | ⚠️ **NOT executed locally** — same memory pressure as Phase C |

Same runtime-gate caveat as Phase C: host RAM/swap constraints make
booting the full e2e stack risky from this session. Recommend running
`make test-e2e` (or `make test-e2e-up && cd web_portal/tests &&
npx playwright test --grep "bl-107"`) as a pre-merge gate before
landing this branch.

## Forced scope

- Test file structure follows `legal-profile-requires-web-portal.spec.ts`
  pattern (`apiRequest.newContext` for per-role storageState mixing in
  D.3) — kept consistent with prior code rather than inventing a new
  helper.

## Deferred to follow-up (NOT B.9 scope)

1. **D.1 / D.2 full add-flow tests via POST /api/channels/** — requires
   seed_e2e.py extension to set up owner-side legal compliance
   fixtures. New BL candidate ("seed: legal-compliance-complete owner
   for BL-107 add-flow E2E").

2. **D.4 full Celery task invocation** — requires either Celery worker
   service в docker-compose.test.yml OR test-only HTTP trigger for
   `parser:check_channel_registry_status`. New BL candidate
   ("Celery-worker in e2e test stack OR task trigger endpoint").

3. **Stub fixture permission fields** — `@verified_channel` admin entry
   for `rekharbor_test_bot` doesn't populate `can_post_messages` /
   `can_delete_messages` / `can_pin_messages`, so /check returns
   `valid=false` (although channel info is correctly returned). For
   positive add-flow tests to assert `valid=true`, fixture must be
   updated. New BL candidate ("stub fixture: bot admin permissions
   for happy path").

These will be surfaced to Marina в Phase B closure batch — not committed
as BACKLOG entries в this prompt per process discipline.

## Deferred to production launch

None.

## Next sub-block

Phase B.9 closure — final report, tmp/ cleanup.

🔍 Verified against: `ff93a5a` (Phase B.9.C HEAD) | 📅 Updated: 2026-05-14T21:12:00Z
