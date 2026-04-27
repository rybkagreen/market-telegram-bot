# Phase 2 Research — Agent C: Defensive scan of existing state-change logging

Scope: feed inventory of every place that already records "metadata about a
placement state change" so the Pydantic `TransitionMetadata` model in Phase 2
neither duplicates nor inherits PII from existing channels. Defensive scan —
not enumeration. Read-only.

Working dir: /opt/market-telegram-bot
Branch: feature/fz152-legal-hardening (Phase 2 work-in-progress sibling
context — Phase 2 itself lives on feature/placement-transition-service)

---

## 1. Inventory: what is already logged on (or near) a state change

| # | Source (file:line / table) | Fields written | Trigger | Retained in DB? |
|---|---|---|---|---|
| 1 | `audit_logs` table — `src/db/models/audit_log.py:11` | `user_id`, `action` (READ/WRITE/DELETE/ADMIN_READ/ADMIN_WRITE), `resource_type`, `resource_id`, `target_user_id`, `ip_address`, `user_agent`, `extra` (JSON), `created_at` | every sensitive-prefix request via `AuditMiddleware`; explicit calls in admin.py | YES — append-only (`REVOKE UPDATE,DELETE`) |
| 2 | `AuditMiddleware.dispatch` — `src/api/middleware/audit_middleware.py:73-78` | `extra={"path", "method", "aud"}` + ip + user-agent + user_id (from `request.state.user_id`) | every 2xx/3xx response on `/api/legal-profile`, `/api/contracts`, `/api/acts`, `/api/ord` | YES (audit_logs row) |
| 3 | `admin.py` legal-profile verify/unverify — `src/api/routers/admin.py:384-391, 414-421` | `action="ADMIN_WRITE"`, `target_user_id`, `extra={"action": "verify"\|"unverify"}` | admin POST `/api/admin/legal-profiles/{id}/verify` | YES (audit_logs) |
| 4 | `admin.py` platform settings update — `src/api/routers/admin.py:554-560` | `action="ADMIN_WRITE"`, `extra={"fields_updated": [...]}` | PUT `/api/admin/platform-settings` | YES (audit_logs) |
| 5 | `publication_logs` table — `src/db/models/publication_log.py:29` | `placement_id`, `channel_id`, `event_type` (`published`, `monitoring_ok`, `deleted_by_bot`, `erid_missing`, `erid_ok`, `bot_removed`, `publish_failed`, …), `message_id`, `post_url`, `erid`, `extra` (JSONB), `detected_at` | every publication lifecycle event | YES — append-only, evidentiary for disputes |
| 6 | `PublicationService.publish_placement` — `src/core/services/publication_service.py:232-267` | `event_type=erid_ok\|erid_missing\|published\|publish_failed`, `extra={"error": str(e)}` on TelegramBadRequest | escrow → published transition | YES (publication_logs) |
| 7 | `PublicationService.delete_published_post` — `src/core/services/publication_service.py:378-384` | `event_type="deleted_by_bot"`, `message_id` | published → completed transition | YES (publication_logs) |
| 8 | `Transaction` table — `src/db/models/transaction.py:49` | `user_id`, `type`, `amount`, `placement_request_id`, `description` (Text), `meta_json` (JSON), `idempotency_key` (UNIQUE) | every escrow_freeze / release / refund / commission | YES (transactions) |
| 9 | `BillingService` Transaction inserts — `src/core/services/billing_service.py:87,150,439,542,767,870,956,1053,1167,1291,1314,1449,1470,1542,1615` | `description=f"Пополнение через {payment_method}"`, `meta_json={...}` | every financial side-effect of a state change | YES (transactions) |
| 10 | `placement_requests.rejection_reason` — `src/db/models/placement_request.py:103` | free-form `Text` | reject() flow → cancelled | YES (column on row) |
| 11 | `placement_requests.meta_json` — `src/db/models/placement_request.py:157` | unstructured JSONB on placement | misc., e.g. failed-permissions context (`billing_service.py:867`) | YES |
| 12 | `reputation_history` table — `src/db/models/reputation_history.py:37` | `user_id`, `role`, `action`, `delta`, `score_before`, `score_after`, `placement_request_id`, `description` | reputation side-effect of state change (publication, cancel, reject, dispute) | YES (append-only by convention) |
| 13 | Celery `BaseTask.on_success/on_failure/on_retry` — `src/tasks/celery_app.py:313-367` | `extra={"task_id", "task_args", "task_kwargs", "traceback"}` to logger; Sentry breadcrumb on retry | every task lifecycle | NO — log stream only (Sentry capture if dsn set) |
| 14 | `placement_tasks.py` SLA / publish flows — `src/tasks/placement_tasks.py:180,212-217,282,312,387,420,461,491-497,541,734-776` | f-string `logger.info/warning/error` mixing `placement.id`, `placement.status`, `member.status`, `error str` | every SLA expiry, publish, retry decision | NO — log stream only |
| 15 | `placement_request_service.py` notification log lines — `src/core/services/placement_request_service.py:56,70,84,…` | `f"Failed to send notification for placement {placement.id}: {e}"` | each transition that emits a notify side-effect | NO — log stream only |
| 16 | `feedback.py` admin status change — `src/api/routers/feedback.py:321` | `f"Admin {admin_user.id} updated status of feedback #{feedback_id} to {body.status}"` | admin feedback transition | NO — log stream only |
| 17 | `auth.py` ticket flow — `src/api/routers/auth.py:72,90,275,333,347,368,390` | `extra={"event", "ip", "user_id", "jti_prefix", "count", "reason"}` | ticket issue / consume / fail (auth state, not placement) | NO — log stream only (out of scope but flagged for PII below) |
| 18 | `payout_service.py` log lines — `src/core/services/payout_service.py:783,793,841,851` | `extra={"payout_id", "status"}` | payout state changes | NO — log stream only |

**Key takeaway for Phase 2 modelling**

- The application already has *three* persisted "state-change" channels:
  `audit_logs`, `publication_logs`, `transactions` (+ `meta_json`/
  `rejection_reason` columns directly on `placement_requests`).
- A new `transition_metadata` JSONB column would be a **fourth**. The Pydantic
  schema must explicitly avoid duplicating data already covered by
  `audit_logs.extra` (admin actions) and `transactions.idempotency_key`/
  `meta_json` (financial idempotency / details).

---

## 2. Возражения и риски (raised before recommendations — meta-rules)

### O-1 (PII / FZ-152) — `audit_logs.user_id` and `target_user_id` are **internal user PKs**, not telegram IDs. Confirmed safe. ✅
`AuditLog.user_id` (line 21) and `target_user_id` (line 29) are `BigInteger`,
populated from `request.state.user_id` (FastAPI auth dep, our internal
users.id). Not telegram IDs. No FZ-152 issue here.

### O-2 (PII) — `audit_logs.ip_address` and `user_agent` are PII.
`AuditMiddleware` writes `request.client.host` (real client IP) and the
raw `user-agent` header for every sensitive-route hit. Under FZ-152 these
are **personal data** (identifiers tied to a natural person). Currently
retained indefinitely (no purge job in `cleanup_tasks.py` for `audit_logs`).
**Out of scope for Phase 2** — this is the existing audit channel, not
the new `metadata_json`. **Phase 2 must not copy these fields into
`metadata_json`.** Stash for Phase 3 backlog: define retention policy
for `audit_logs.ip_address`/`user_agent` (e.g. 90-day rolling purge).

### O-3 (PII) — `auth.py` log lines write `user_id` + `ip` to log stream (not DB), but at WARN level → ends up in Sentry/GlitchTip via integration.
`auth.py:88-95, 333-373` log `user_id`, `ip`, `count` on rate-limit
events. WARN-level events cross the Sentry breadcrumb bar by default.
Means external Sentry instance receives our internal user_id ↔ IP
correlations. **Out of scope for Phase 2** — concerns the auth subsystem,
not placement state. Stash: review Sentry `before_send` hook to scrub
ip from `extra`.

### O-4 (architectural smell) — `placement_requests.rejection_reason` (Text) and `meta_json` (JSONB) are unstructured catch-alls already on the row.
Both fields exist today. `rejection_reason` is free-form text typed by
owners ("не подходит по тематике") — **definitely PII-risk** because
owners can paste anything. `meta_json` is JSONB used by
`billing_service.py:867` to record `failed_permissions` context. **The
new `metadata_json` should not become a fourth catch-all next to these
two.** If Phase 2 introduces metadata_json, Phase 2 should clearly
document the boundary: structured non-PII facts only; free-form goes
to `rejection_reason` (already PII-tainted, scope of FZ-152 retention
review).

### O-5 (architectural smell) — `Transaction.description` is free-form Russian text and `Transaction.meta_json` is unstructured.
`billing_service.py:92,155` write descriptions like `f"Пополнение через
{payment_method}"`. `meta_json` is used both for actual metadata AND as
processed-marker (`existing.meta_json.get("processed")` —
`billing_service.py:1143`). This is the same anti-pattern Phase 2 is
asked to avoid for `metadata_json`. Phase 2's TransitionMetadata Pydantic
model is the *right* choice precisely to avoid this drift on the new
column. **Recommend explicit ADR comment near the new column: "schema-
controlled, NOT a free-form catchall".**

### O-6 (correctness) — `f"Failed to send notification for placement {placement.id}: {e}"` (placement_request_service.py:56) and similar lines bury structured info in unstructured strings.
Across `tasks/placement_tasks.py` and `core/services/`, status
transitions, error reasons, member statuses, and retry counts are
embedded in f-strings. None of it is queryable. **The `metadata_json`
column is the right fix for the structured subset.** Phase 2's job is
to identify *which* of these grep-able log facts deserve promotion to
queryable JSON — `error_code`, `gate_attempt`, `task_name` from the
user's starter set already cover the pattern. Good direction.

### O-7 (footgun) — `from_admin_id: int | None` in starter set is structurally identical to existing `audit_logs.user_id` for admin-initiated transitions.
If an admin triggers a state change via API, the `AuditMiddleware` (or
explicit `audit.log()` call in admin.py) already records the admin's
internal user_id with `action="ADMIN_WRITE"`. Adding `from_admin_id` to
`TransitionMetadata` duplicates that fact. The arguments **for** keeping
it: (a) `audit_logs` is keyed by `resource_type` + `resource_id`, so
joining audit → placement requires a query; embedding the admin id on
the transition itself is faster for "show me the audit trail for
placement N" queries. (b) audit_logs can be incomplete if the admin path
bypassed sensitive-prefix middleware (e.g. internal admin tools, future
GraphQL paths). I lean **keep** but flag the duplication explicitly so a
future maintainer doesn't strip it thinking "audit_logs already has it".

### O-8 (PII) — `telegram_id` MUST NOT be added to metadata_json even though it's omnipresent in current logging.
The user's instruction is explicit. Current log lines like `_notify_user
(placement.advertiser_id, …)` use the **internal user.id**, not
telegram_id (verified: `placement.advertiser_id` is FK to users.id, not
telegram). However, several Celery task log lines do flow through to
`mailing:notify_user` which takes `telegram_id` directly. **No
metadata_json field should accept a telegram_id.** Confirming Phase 2
boundary: if a transition needs to point at "the user who did this", use
internal `user_id` (matches existing audit_logs convention).

---

## 3. Рекомендация для Pydantic TransitionMetadata

### Starter set evaluation

| Field | Verdict | Reason |
|---|---|---|
| `task_name: str \| None` | **KEEP** | Not redundant — Celery `BaseTask.on_success` writes `task_name` to log stream only (not DB). Promoting it to the structured column is the explicit value-add. Non-PII (e.g. `placement:publish_placement`). |
| `error_code: str \| None` | **KEEP** | Currently buried in `f"Error publishing placement {id}: {e}"` log strings (placement_tasks.py:465,541) — no structured field. Phase 2 should constrain this to **enum / Literal** (e.g. `"telegram_bad_request"`, `"bot_not_admin"`, `"erid_missing"`), not free-form `str`, to prevent paste-an-exception-message footgun. **Sub-recommendation: type as `Literal[...]`** matching the publication_logs `event_type` enum + financial codes. |
| `gate_attempt: int \| None` | **KEEP** | Not in any current logging. Maps to Celery `self.request.retries` semantics but is decoupled from Celery (works for non-Celery transitions too). Non-PII. |
| `from_admin_id: int \| None` | **KEEP, document overlap** | Duplicates `audit_logs.user_id` for admin paths (see O-7). Internal user.id, not telegram. Non-PII per O-1. Convenience for "audit trail of this placement" queries. |
| `celery_task_id: str \| None` | **KEEP** | Currently in log `extra={"task_id": …}` only (celery_app.py:327). Promoting it joins the structured trail to Sentry / log aggregator. UUID, non-PII. |

→ **None of the starter set is redundant** — every field surfaces info
that today exists only in unstructured log strings.

### Fields to ADD (non-PII only, FZ-152 clean)

| Field | Type | Source in existing logging | Non-PII justification |
|---|---|---|---|
| `from_status: PlacementStatus` | enum | `repo.update_status()` reads `placement.status` before assigning — currently *not* logged anywhere structured. This is the load-bearing fact of "state change". | Enum value, no user data. |
| `to_status: PlacementStatus` | enum | Same as above (the new value). | Enum value. |
| `trigger: Literal["api", "celery_beat", "celery_signal", "admin_api", "system"]` | enum | Implicit in caller — currently inferable only by reading the stack trace. Distinguishes "auto-cancellation by SLA" vs. "admin-forced cancel". | Categorical. |
| `idempotency_key: str \| None` | str | `Transaction.idempotency_key` pattern (`escrow_release:placement={id}:owner`). If the transition is paired with a financial event, copying its key here makes the link explicit and queryable. | Synthetic key, no user data. |
| `correlation_id: str \| None` | UUID-string | Currently nothing — would be the missing link tying multi-step transitions (API → Celery → notify). Set once at the originating request and propagated. | UUID, non-PII. |

**Optional (defer if minimalism is preferred):**

| Field | Why optional |
|---|---|
| `placement_id: int` | Already implied by row key if `metadata_json` is a column on `placement_requests`. Duplication only useful if metadata_json moves to a separate `placement_transitions` table. **Decision depends on Phase 2 storage choice — agent A/B should be cross-referenced.** |
| `attempted_at: datetime` | Mostly duplicates the row's `updated_at`. Skip unless Phase 2 separates "attempted but failed" from "succeeded". |

### Fields to REMOVE from starter set as redundant

→ **None.** All five starter fields surface info that's currently
unstructured.

### Fields flagged as PII — MUST NOT be added even though they appear in existing logging

| Field | Where it appears today | FZ-152 reason |
|---|---|---|
| `telegram_id` | `mailing:notify_user(telegram_id, …)`, `_notify_user_async`, log f-strings in notification_tasks.py | Direct identifier of a natural person on Telegram. FZ-152 personal data. (See O-8.) |
| `ip_address` | `audit_logs.ip_address` (existing), `auth.py extra={"ip": …}` | Article 3 152-ФЗ: indirect identifier of a natural person. Already present in audit_logs (O-2 backlog). |
| `user_agent` | `audit_logs.user_agent` (existing) | Browser fingerprint — quasi-identifier under GDPR/152-ФЗ when combined with other fields. |
| `rejection_reason` text | `placement_requests.rejection_reason` (free-form owner input) | User-typed free-form text — can contain anything (phone, name, email). Must stay in its dedicated column with appropriate FZ-152 retention; not duplicated into metadata_json. |
| `phone_number`, `email`, `inn`, `passport_*`, `bank_account`, `legal_name` | `legal_profiles` table, log_sanitizer.SENSITIVE_FIELD_NAMES | Direct PII per 152-ФЗ Article 10 (special categories partially). Already redacted in error responses; never log to metadata_json. |
| Free-form `description` / `comment` / `note` accepting user input | `Transaction.description`, `placement_requests.counter_comment` | User-controllable string → unbounded PII risk. Use enum `error_code` instead (already in starter set). |

---

## 4. Defer-list (one-line footnotes, not Phase 2 scope)

- F-1: `cleanup_tasks.py` has no purge for `audit_logs.ip_address`/`user_agent` — define retention in Phase 3.
- F-2: `Sentry before_send` hook should scrub `extra.ip` / `extra.user_id` from auth.py warn-level events — Phase 3 backlog.
- F-3: `placement_requests.rejection_reason` should join the FZ-152 retention review (free-form text column accepting user input).
- F-4: Consider migrating ad-hoc `f"Error processing placement {id}: {e}"` log lines (placement_tasks.py x6) onto `logger.error("…", extra={"placement_id": id, "error": str(e)})` — purely cosmetic, deferred.

---

## 5. Final recommendation summary

`TransitionMetadata` should be a **closed Pydantic model** (no `extra =
"allow"`), comprising:

```
# starter (5)
task_name: str | None
error_code: Literal[...] | None      # constrained, not free-form str
gate_attempt: int | None
from_admin_id: int | None             # internal users.id, NOT telegram_id
celery_task_id: str | None

# add (3 strong + 2 conditional)
from_status: PlacementStatus
to_status: PlacementStatus
trigger: Literal["api", "celery_beat", "celery_signal", "admin_api", "system"]
idempotency_key: str | None           # links to Transaction.idempotency_key
correlation_id: str | None            # request-scoped UUID

# defer to Phase 2 storage decision
placement_id: int                     # only if column moves to separate table
attempted_at: datetime                # only if separating attempts from successes
```

**Why this passes FZ-152:** every field is either an enum, an internal
PK (users.id, placement.id), a synthetic key (idempotency_key,
correlation_id, celery UUID), or a constrained `Literal`. No
free-form user input. No telegram_id, ip, ua, phone, inn, passport,
email, or legal name.

**Why this is non-redundant:** every field promotes a fact that today
lives only in unstructured log strings. None duplicates audit_logs
(which is keyed by resource_type/id, not by transition), and none
duplicates Transaction.meta_json (which is financial — different
domain).

---

🔍 Verified against: 016c4c9a5498267905ec28afdd31666a598c1be4 | 📅 Updated: 2026-04-26T00:00:00Z
