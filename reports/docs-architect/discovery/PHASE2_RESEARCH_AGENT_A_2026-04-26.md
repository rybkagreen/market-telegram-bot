# Phase 2 Research — Agent A — Direct mutation inventory of `PlacementRequest.status`

Scope: `src/core/`, `src/api/`, `src/tasks/`, `src/bot/handlers/`. Excluded: `tests/`, `src/db/migrations/`, `scripts/`, `src/db/repositories/` (out of stated scope, but cross-referenced where in-scope code calls them — see §1b).

Mode: research / planning. No code change introduced — only an inventory and objections.

---

## 1. Direct mutation points (in-scope: src/core, src/api, src/tasks, src/bot/handlers)

| file:line | from_status | to_status | actor_context | mutation_type |
|-----------|-------------|-----------|---------------|---------------|
| `src/core/services/publication_service.py:221` | `escrow` (asserted by guard upstream — T4 publish path) | `failed` | service `PublicationService.publish_placement` — called from celery task `placement:publish_placement` (per-task `ephemeral_bot()` + own session) | single_row_orm |
| `src/core/services/publication_service.py:260` | `escrow` | `failed` | same — `PublicationService.publish_placement` after `TelegramBadRequest` on send | single_row_orm |
| `src/core/services/publication_service.py:301` | `escrow` (after own commit at L291; placement re-fetched at L294) | `published` | same — `PublicationService.publish_placement` happy path | single_row_orm |
| `src/core/services/publication_service.py:401` | `published` (guarded at L342–L350) | `completed` | service `PublicationService.delete_published_post` — called from celery task `placement:delete_published_post` | single_row_orm |
| `src/core/services/placement_request_service.py:617` | `counter_offer` (asserted L607) | `pending_owner` | service `PlacementRequestService.advertiser_counter_offer` — called from API `_action_counter_reply` (`PUT /api/placements/{id}` action=counter-reply) | single_row_orm |
| `src/tasks/notification_tasks.py:1043` | `pending_owner` (filtered in SELECT L1033 + 24h age) | `pending_payment` | celery task `notifications:auto_approve_placements` (Beat hourly, queue `mailing`) — owns its session, `for_update` lock | single_row_orm (in loop over selected rows) |
| `src/tasks/placement_tasks.py:637` | `failed` (asserted L623) | `escrow` | celery task `placement:retry_failed_publication` (queue `worker_critical`) — restores status before re-running publish path | single_row_orm |
| `src/tasks/placement_tasks.py:892` | `escrow` (filtered in SELECT L855, `message_id IS NULL`, `final_schedule <= now`) | `failed` | celery task `placement:check_escrow_sla` (Beat 5 min, queue `worker_critical`) — own session + `for_update` not used | single_row_orm (in loop) |
| `src/tasks/placement_tasks.py:1248` | `escrow` (filtered in SELECT L1188, `scheduled_delete_at < now-48h`) | `failed` | celery task `placement:check_escrow_stuck` group B (Beat, queue `worker_critical`) | single_row_orm (in loop) |
| `src/tasks/dispute_tasks.py:108` | `escrow` / `published` / `failed` (any — task does not assert) | `refunded` / `published` / `refunded` (computed L57–L93 from `resolution`) | celery task `dispute:resolve_financial` (queue `worker_critical`) — see objection O-1, **no live dispatcher in repo** | single_row_orm |
| `src/tasks/cleanup_tasks.py:154` | `failed` ∪ `cancelled` ∪ `refunded` (set in WHERE L148–L152) | `failed` | celery task `cleanup:archive_old_campaigns` (queue `cleanup`) — set-based `update(...)` over rows older than `months*30` days | bulk_update |
| `src/api/routers/disputes.py:704` | `escrow` / `published` / `failed` (any — router does not assert before mutation) | `refunded` / `published` / `refunded` (computed L662–L685 from `body.resolution`) | request-scoped, router `POST /api/admin/disputes/{id}/resolve` (admin-auth) — direct `placement.status = ...` after billing call | single_row_orm |
| `src/bot/handlers/owner/arbitration.py:197` | `pending_owner` ∪ `counter_offer` (asserted L190) | `pending_payment` | bot handler `accept_request` (callback `own:accept:<id>`) — direct mutation on `req` from `session.get`, immediate `session.commit()` | single_row_orm |
| `src/bot/handlers/owner/arbitration.py:294` | not asserted (any — only `req` existence checked at L289) | `cancelled` | bot handler `reject_request_comment` (FSM final step) — owner reject with comment | single_row_orm |
| `src/bot/handlers/owner/arbitration.py:502` | not asserted (any — only `req` existence checked at L492) | `counter_offer` | bot handler `_send_counter_offer` (called from FSM finishers in same file) | single_row_orm |
| `src/bot/handlers/advertiser/campaigns.py:199` | `counter_offer` (asserted L191) | `pending_payment` | bot handler `camp_counter_accept` (callback `camp:counter:accept:<id>`) — advertiser accepts owner counter-offer | single_row_orm |
| `src/bot/handlers/advertiser/campaigns.py:294` | not asserted (only `req` existence at L286) | `pending_owner` | bot handler `camp_counter_input` (FSM input handler) — advertiser counter-reply | single_row_orm |
| `src/bot/handlers/placement/placement.py:615` | `escrow` (asserted L582) | `cancelled` | bot handler `cancel_after_escrow` (callback `camp:cancel_after_escrow:<id>`) — advertiser cancels with 50% refund | single_row_orm |
| `src/bot/handlers/admin/disputes.py:252` | not asserted (any — `req` existence at L192) | `refunded` / `published` / `refunded` (computed L213–L240 from `verdict`) | bot handler `verdict_callback` (admin verdict on dispute) | single_row_orm |

### 1b. Indirect mutation — service calls into repo helpers (cross-reference)

These do not write `placement.status =` directly inside the in-scope tree, but they reach the same field via a thin wrapper in `src/db/repositories/placement_request_repo.py`. They are NOT included in the table above (per scope), but a transition service must replace these as well or the bypass remains. Listed for completeness:

| call site (in-scope) | repo helper (out of scope) | resulting status |
|----------------------|----------------------------|------------------|
| `src/core/services/placement_request_service.py:373` (`owner_accept`) | `placement_repo.accept` → L213 `pending_payment` | `pending_payment` |
| `src/core/services/placement_request_service.py:444` (`owner_reject`) | `placement_repo.reject` → L231 `cancelled` | `cancelled` |
| `src/core/services/placement_request_service.py:507` (`owner_counter_offer`) | `placement_repo.counter_offer` → L251 `counter_offer` | `counter_offer` |
| `src/core/services/placement_request_service.py:561` (`advertiser_accept_counter`) | `placement_repo.accept` | `pending_payment` |
| `src/core/services/placement_request_service.py:721` (`advertiser_cancel`) | `placement_repo.reject` | `cancelled` |
| `src/core/services/placement_request_service.py:773` (`_freeze_escrow_for_payment` ← called from `process_payment`) | `placement_repo.set_escrow` → L270 `escrow` | `escrow` |
| `src/core/services/placement_request_service.py:879` (`process_publication_success`, marked DEPRECATED) | `placement_repo.set_published` → L286 `published` | `published` |
| `src/core/services/placement_request_service.py:924+930` (`process_publication_failure`) | `placement_repo.update_status` × 2 → L198 (any new_status) | `failed` then `refunded` |
| `src/core/services/placement_request_service.py:968` (`auto_expire`, called from celery) | `placement_repo.reject` | `cancelled` |
| `src/api/routers/campaigns.py:326` (`POST /api/campaigns/{id}/start`, advertiser-auth) | `placement_repo.update_status` | `pending_payment` |
| `src/api/routers/campaigns.py:378` (`POST /api/campaigns/{id}/cancel`, advertiser-auth) | `placement_repo.update_status` | `cancelled` |

See objection O-3 about the parallel paths.

---

## 2. Bulk mutation points

Only one bulk mutation hits `PlacementRequest.status`.

| file:line | placements selected by | metadata_per_row_identical? | candidate for `bulk_transition()` |
|-----------|------------------------|-----------------------------|-----------------------------------|
| `src/tasks/cleanup_tasks.py:145` (set-based `update(PlacementRequest).where(...).values(status=PlacementStatus.failed)`) | `created_at < now()-months*30 days AND status IN {failed, cancelled, refunded}` | **yes** in the strict sense — `.values()` writes only `status`; no per-row metadata is computed. **but**: the call sets terminal `failed` over rows that are already terminal (`failed`/`cancelled`/`refunded`) — this is not a real status transition, it is a normalisation pass that arguably should not exist (see O-2). | **borderline** — bulk transition is technically applicable, but the semantics are a no-op-in-disguise; before wiring it through the new service, decide whether the call should be deleted (O-2) instead of wrapped. |

Note: `src/core/services/ord_service.py:186` and `src/core/services/link_tracking_service.py:117` are bulk `sa_update(PlacementRequest)` calls but mutate `erid` / `clicks_count`, not `status`. Out of inventory.

---

## 3. Celery tasks mutating `placement.status`

| task name (full `@celery_app.task name=`) | file:line of mutation | task signature args | call-sites (dispatchers) |
|-------------------------------------------|----------------------|---------------------|--------------------------|
| `notifications:auto_approve_placements` (queue `mailing`) | `src/tasks/notification_tasks.py:1043` | `()` — no args, scheduler-driven | Celery Beat only. No code-level dispatcher in repo. → `actor_user_id=None` (system actor). |
| `placement:publish_placement` (queue `worker_critical`) | mutates via service at `src/core/services/publication_service.py:221, 260, 301` | `(placement_id: int)` | `src/tasks/placement_tasks.py:965` (from `schedule_placement_publication`). Indirect chain: `placement_request_service.process_payment` → `_schedule_publication_task` → `schedule_placement_publication.delay(...)` → `publish_placement.apply_async(...)`. → no human actor; `actor_user_id=None`. |
| `placement:retry_failed_publication` (queue `worker_critical`) | `src/tasks/placement_tasks.py:637` | `(placement_id: int)` | No live `.delay` / `.apply_async` call found anywhere in `src/`. → either dead, or dispatched only by ops/admin manually. See O-4. |
| `placement:check_escrow_sla` (queue `worker_critical`) | `src/tasks/placement_tasks.py:892` | `()` — Beat 5 min | Celery Beat only (`celery_app.py` schedule). → `actor_user_id=None`. |
| `placement:check_escrow_stuck` (queue `worker_critical`) | `src/tasks/placement_tasks.py:1248` | `()` — Beat | Celery Beat only. → `actor_user_id=None`. |
| `placement:delete_published_post` (queue `worker_critical`) | mutates via service at `src/core/services/publication_service.py:401` | `(placement_id: int)` | `src/tasks/placement_tasks.py:1118` (from `check_scheduled_deletions`), `:1232` (from `check_escrow_stuck` group A), `:1291` (from group C). → all scheduler-driven; `actor_user_id=None`. |
| `dispute:resolve_financial` (queue `worker_critical`) | `src/tasks/dispute_tasks.py:108` | `(dispute_id, resolution, placement_request_id, final_price, advertiser_id, owner_id)` | **No dispatcher anywhere** — confirmed `grep -rn "resolve_dispute_financial\|dispute:resolve_financial" src/`. The active dispute-resolution paths (router `disputes.py:704`, bot handler `admin/disputes.py:252`) inline the same logic without dispatching this task. See O-1. → if revived, the dispatcher would already know `admin_user.id`, so signature should accept `actor_user_id: int` (not `None`). |
| `cleanup:archive_old_campaigns` (queue `cleanup`, but defined inside `cleanup_tasks.py` whose pattern routes to `worker_background`) | `src/tasks/cleanup_tasks.py:154` | `(months: int = 12)` | No live dispatcher in `src/`; Beat schedule unverified by this audit (see O-5). → `actor_user_id=None`. |

**Summary of actor_user_id propagation requirement:**
- Tasks that need `actor_user_id: int` in signature (caller has it): only `dispute:resolve_financial` (if revived).
- Tasks for which `actor_user_id=None` is the right default (scheduler / system): the remaining six.

---

## 4. Dead-code / redundancy candidates

| symbol | file:line | reason |
|--------|-----------|--------|
| `dispute:resolve_financial` celery task | `src/tasks/dispute_tasks.py:18-120` | Zero dispatchers in `src/` (verified by grep). The two live dispute-resolution paths — `src/api/routers/disputes.py:704` and `src/bot/handlers/admin/disputes.py:252` — inline the billing+status-mutation logic synchronously inside the request, not via this task. Once `PlacementTransitionService.transition()` lands, the inline paths consolidate; this orphan task should be deleted in the same PR (or wired in if it was meant to be the canonical async path — see O-1). |
| `PlacementRequestService.process_publication_success` | `src/core/services/placement_request_service.py:846-888` | Header docstring marks it `DEPRECATED v4.2`. No callers found in scope (`grep`). Keeping it alongside `PublicationService.publish_placement` (the live path) splits the `escrow → published` transition between two services. Candidate for deletion when transition service centralises `published`. |
| `PlacementRequestService.process_publication_failure` | `src/core/services/placement_request_service.py:890-936` | Calls `placement_repo.update_status` twice (`failed` then `refunded`) — the only in-scope path that writes two transitions in one method. No live dispatcher confirmed (the live `failed` transitions all happen in `placement_tasks.py`). Verify before deletion, but very likely orphan. |
| `placement_repo.update_status` / `accept` / `reject` / `counter_offer` / `set_escrow` / `set_published` | `src/db/repositories/placement_request_repo.py:191-289` | These are thin direct-mutation helpers (out of stated scope, but reachable from in-scope code per §1b). After `PlacementTransitionService.transition()` becomes the canonical entrypoint, these helpers become a parallel mutation API and must either be deleted or re-implemented as private inner steps of the transition service. Otherwise a future contributor who imports `PlacementRequestRepo` keeps writing the bypass. See O-3. |
| `placement:retry_failed_publication` celery task | `src/tasks/placement_tasks.py:583-642` | No `.delay` / `.apply_async` call found in `src/`. Either dead, or used only by ops via `celery call ...`. The task also sets `failed → escrow` without releasing or re-checking the escrow transaction — see O-6. |

---

## 5. Возражения и риски (Objections and risks)

### O-1 — `dispute:resolve_financial` task is parallel-implementation orphan, with diverging behaviour

The Celery task at `src/tasks/dispute_tasks.py:18-120` and the synchronous router path at `src/api/routers/disputes.py:639-706` (and bot handler at `src/bot/handlers/admin/disputes.py:200-253`) implement the **same** dispute resolution flow — billing scenario chosen from `resolution`, placement status set to `refunded`/`published`/`refunded`. Yet:

1. The task has no dispatcher anywhere (`grep -rn` clean) — it cannot fire.
2. The router path violates the S-48 transaction contract by calling `await session.commit()` inline at `disputes.py:706` after `placement.status = new_status` — a router is the outermost transaction owner here, but combining inline billing mutations and status mutation in one endpoint duplicates what the task would do asynchronously.
3. The bot-handler path is a third copy.

For Phase 2 the right call is **not** to wrap all three call-sites in `transition()` blindly: first decide whether the canonical path is sync or async. If sync — delete the task and the bot-handler copy, route the bot through the API. If async — delete the inline router/handler bodies, dispatch the task, and accept the eventual-consistency delay before status changes for admin users.

I prefer **sync** because dispute resolution shows the admin a result page; an async path opens a window where the admin sees the dispute resolved but `placement.status` not yet updated, which feeds bug reports.

### O-2 — `cleanup:archive_old_campaigns` mutates already-terminal rows

`src/tasks/cleanup_tasks.py:140-156`:

```python
update(PlacementRequest)
  .where(
      PlacementRequest.created_at < cutoff_date,
      PlacementRequest.status.in_([PlacementStatus.failed, PlacementStatus.cancelled, PlacementStatus.refunded]),
  )
  .values(status=PlacementStatus.failed)
```

This rewrites `cancelled → failed` and `refunded → failed` for any row older than `months*30` days. That is not archival — it is data-loss-by-overwrite of two distinct terminal states. If the original intent was "mark archived" the column should be a separate `is_archived` flag, not the `status` enum. If the intent was "delete old rows" the task should DELETE, not UPDATE. Either way, wrapping this in `bulk_transition()` legitimises a bug; raise as a sprint-level question, not just a refactor target.

### O-3 — Two parallel mutation APIs (`placement.status =` direct + `placement_repo.<helper>`) cannot coexist with `PlacementTransitionService`

Out of the 19 mutation points in §1, **9 are direct attribute writes** in services / handlers, and **11 more reach the field via `placement_repo.{accept,reject,counter_offer,set_escrow,set_published,update_status}`**. The repo helpers each do `placement.status = X; await session.flush(); await session.refresh(...)` — they are functionally a third copy of "transition logic without invariants".

If Phase 2 leaves these helpers in place after introducing `PlacementTransitionService.transition()`:
- Any new code that imports `PlacementRequestRepository` re-introduces the bypass.
- The old service methods (`PlacementRequestService.owner_accept` etc.) keep calling the repo helpers, so the new transition service is an alternative, not a replacement.

Recommendation: in the same PR that ships `transition()`, either (a) delete the six repo helpers and rewrite the eleven callers to go through the service, or (b) gut the helpers' bodies into thin `await self._transition_service.transition(...)` calls and forbid further use. The second option preserves the repo's import surface but makes the bypass intentional. Either way the choice must be made — leaving both APIs alive is the worst outcome.

### O-4 — `placement:retry_failed_publication` skips escrow re-validation

`src/tasks/placement_tasks.py:637` sets `failed → escrow`. The escrow funds may have already been refunded if the row hit `check_escrow_sla` (which refunds + marks `failed`) before this task ran. Resetting status to `escrow` does not restore the `escrow_transaction_id` invariant (INV-1, documented at `placement_request_service.py:746`: `placement.status='escrow' ⇒ escrow_transaction_id IS NOT NULL`). If the refund already executed, the status flip leaves an inconsistent row that any subsequent `release_escrow` call will compound.

This is a latent bug independent of Phase 2 — but Phase 2's `transition()` is exactly where the invariant check should live. Whoever implements `transition()` must add INV-1 as a precondition for `→ escrow`, and `retry_failed_publication` must be rewritten to detect the refunded case before the transition.

### O-5 — `cleanup:archive_old_campaigns` queue-routing is ambiguous

Per CLAUDE.md the task prefix `cleanup:*` routes to `worker_background`. The decorator at `src/tasks/cleanup_tasks.py:101` is `@celery_app.task(bind=True, base=BaseTask, name="cleanup:archive_old_campaigns")` — no explicit `queue=`. The CLAUDE.md "Rules for new tasks" subsection says every task **MUST** have an explicit `queue=`. This task predates the rule but is in scope of Phase 2 inventory; note as audit-finding for the implementer.

### O-6 — Owner reject / counter-offer in bot handler skips status precondition

`src/bot/handlers/owner/arbitration.py:289-294` (`reject_request_comment`) and `:492-502` (`_send_counter_offer`) only check `req` existence, not `req.status`. A stale FSM state would let an owner reject a placement that is already `escrow` or `published`, blowing past the preconditions enforced by `PlacementRequestService.owner_reject` / `owner_counter_offer`. The transition service must reject these calls and the handlers must surface the error to the user — silent state-corruption is the current behaviour.

### O-7 — `PlacementRequestService.process_publication_failure` writes two transitions in one method

`src/core/services/placement_request_service.py:923-933` does `→ failed` then immediately `→ refunded`. The first write is observable for any read-after-write within the session (e.g. a notification task triggered by the flush). With `transition()` the two-step write should become a single `→ refunded` (or a documented two-step with explicit reasoning). Listed as a refactor opportunity inside the same Phase 2 PR.

### O-8 — Status guards by row attribute (`from_status` "any") swallow real bugs

Six in-scope mutation points (rows 13, 15, 16 in §1, plus `disputes.py:704`, `admin/disputes.py:252`) write `placement.status = X` without first asserting `placement.status == expected`. `transition()` makes guards trivial; the question is whether to enforce a single global allow-list per `(from_status, to_status)` or accept admin-override paths (dispute resolution legitimately writes to a published placement). Decide once, document in the service header — otherwise reviewers will keep arguing per-PR.

### O-9 — CLAUDE.md state-machine list is incomplete

CLAUDE.md "PlacementStatus State Machine" lists `pending_owner → counter_offer ↔ pending_payment → escrow → published → (done)`. The actual enum (`src/db/models/placement_request.py:38-50`) also defines `completed` (terminal after `published`, used in `PublicationService.delete_published_post:401`) and `failed_permissions` (defined but no in-scope writer — see O-10). The state machine documentation must be updated as part of Phase 2; otherwise the transition service's allow-list is built against an incomplete spec.

### O-10 — `PlacementStatus.failed_permissions` is defined but unreferenced

`grep -rn "failed_permissions" src/` returns only the enum definition. No in-scope writer transitions to it; no reader filters on it. Either delete the enum value (most likely correct — schema cleanup) or wire it up where `PublicationService` currently uses `failed` for permission-check failures (`publication_service.py:221` after `BotNotAdminError`/`InsufficientPermissionsError`). This is a one-line ambiguity that the transition-service author will hit immediately.

---

## Footnote — possible further improvements (no action required now)

- Unify `_notify_*` helpers used in `arbitration.py` and `campaigns.py` — many duplicate try/except `notify_*` blocks. Cosmetic.
- `src/core/services/publication_service.py:291` calls `await session.commit()` mid-method (saving `message_id` as an idempotent lock). This is intentional and documented but breaks the S-48 "outermost caller owns commit" rule. Worth a one-line note in `PublicationService` docstring; not blocking.

---

🔍 Verified against: 016c4c9a5498267905ec28afdd31666a598c1be4 | 📅 Updated: 2026-04-26T08:12:19Z
