# CHANGES 2026-05-14 — BL-107 Phase B.9 Phase C (Playwright BL-002 unblock)

## Context

Phase B.8 shipped the Telegram Bot API mock infrastructure that BL-002
required (plan-08 noted "needs Telegram Bot API mock wired into
docker-compose.test.yml"). Phase C unwraps the `test.fixme` placeholder
left as a marker, replacing it with a real spec body that exercises the
stub-routed bot call path.

**Scope envelope:** single test file edit (`deep-flows.spec.ts:288-296`),
no infra changes, no fixture changes, no API changes.

Built atop Phase B.9.B (`e0124f2`).

## Empirical decisions

1. **Endpoint chosen: POST /api/channels/check** (not POST /api/channels/).
   Reasons:
   - `/check` exercises both `bot.get_chat()` AND `bot.get_chat_member()` —
     the two stub-routed calls that Phase B.8 wired
   - `/check` does NOT require completed owner-side legal-compliance
     state (G04 legal profile, G05 framework contract, G06 payout method).
     POST /api/channels/ enforces all three via
     `compliance.check_gates_for_user_role` → seeded test owner would
     fail without further seed-fixture work, which is out of Phase C scope.
   - `/check` is the precheck call the owner-adds-channel UI makes BEFORE
     POST /api/channels/ — proving it works through the stub is the
     contract-level proof BL-002 needs.

2. **Stub fixture `@verified_channel`** (15k members, Trustchannelbot +
   rekharbor_test_bot listed as administrators) is the realistic happy
   path — exercises the verification ergonomics that BL-107 added.
   `bot.get_chat(@verified_channel)` returns the chat;
   `bot.get_chat_member(chat_id, bot.id)` returns the admin entry for
   the test bot. Test asserts on response shape (`channel.username`,
   `channel.title`, `bot_permissions` presence) — does NOT assert on
   `valid=true` because Phase B.8 fixture entries do not populate
   `can_post_messages` / `can_delete_messages` / `can_pin_messages`,
   so the response will report `missing_permissions: [post_messages,
   delete_messages, pin_messages]` and `valid: false`. Populating those
   permissions is a Phase D refinement (covered in spec D.1).

3. **Re-using existing `test.use({ storageState: owner.storageFile })`
   pattern** from peer tests in the same file — keeps the spec aligned
   with the suite's authentication model (global-setup.ts mints JWT via
   /api/auth/e2e-login).

## Files modified

- `web_portal/tests/specs/deep-flows.spec.ts` (lines 288-322): replaced
  `test.fixme` body with active `test` body. BL-002 marker (referring to
  `reports/docs-architect/BACKLOG.md`) preserved as an inline comment so
  the historical lineage stays traceable.

## Verification gates

| Gate | Status |
|---|---|
| `npx tsc --noEmit` on `web_portal/tests/` | ✅ clean |
| `npx playwright test --list --grep "channel add"` | ✅ 3 projects × 1 test discovered (no `fixme`) |
| Runtime pass (`make test-e2e`) | ⚠️ **NOT executed locally** — see Deferred section |

## Deferred verification

Full e2e runtime verification (`make test-e2e` or equivalent
`docker-compose.test.yml` stack + playwright run) **was not executed in
this commit**. Reason: current host memory pressure (free RAM ≈ 1.8 GB,
swap 7 GB used per `free -m`) means booting the e2e stack
(postgres-test + redis-test + seed-test + api-test + nginx-test +
telegram-stub) carries OOM risk. Project memory has a standing entry
about Claude Code OOM-kills on this host.

Recommendation: run `make test-e2e` (or `make test-e2e-up && cd
web_portal/tests && npx playwright test --grep "channel add"`) as the
verification gate before merging the feature branch. The static gates
(typecheck, Playwright list, fixture cross-ref) provide structural
correctness; the runtime gate proves the wiring.

## Forced scope

None. Test body kept minimal — happy-path assertion only, on response
shape (not value of `valid`). Phase D (next sub-block) introduces the
4 new specs that exercise positive/negative add-flow paths.

## Deferred to production launch

None — this is test infrastructure consumption, not production code.

## Next sub-block

Phase D — 4 new BL-107 E2E specs (auto-continue per prompt).

🔍 Verified against: `e0124f2` (Phase B.9.B HEAD) | 📅 Updated: 2026-05-14T21:06:00Z
