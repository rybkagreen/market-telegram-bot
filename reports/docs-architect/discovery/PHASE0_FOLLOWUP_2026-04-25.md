# PHASE 0 FOLLOW-UP — Pre-flight findings before Phase 1

**Mode:** research / planning. No production code modified. Branch: `chore/phase0-followup` (off `develop` at `1fd0960`).

**TL;DR:** all four PF checks resolved without surprises. Phase 1 is not blocked by Phase 0 regressions; the 401 vs 426 question and the audit-middleware question both have clear evidence-backed recommendations. **STOP — awaiting decisions on PF.2 status code and PF.4 refactor scope before proceeding to Phase 1.**

| PF | Question | Verdict | Action needed |
|---|---|---|---|
| **PF.1** | Did Phase 0 add new mypy errors? | **Clean — 0 new errors in Phase 0 surface** | Freeze baseline at 10 errors / 5 files (untouched code) |
| **PF.2** | 401 vs 426 for aud-less legacy tokens | **Recommend 426 (no live legacy-token holders)** | Decide: flip in Phase 1 first commit, or keep 401 |
| **PF.3** | Bridge happy-path end-to-end works? | **Pass** — 4-step flow + auth-dep accepts resulting token | Test merged into `tests/integration/`; no blocker |
| **PF.4** | Audit middleware: refactor or parallel file? | **Refactor — ≈ 21 LOC across 2 files** | Decide: §1.B.0 in Phase 1, or defer to Phase 2 ticket |

---

## PF.1 — mypy baseline diff

### Setup
- PRE: `59908b7` (parent of Phase 0 on develop)
- POST: `1fd0960` (Phase 0 merged into develop) — equivalent to `7fe748c` on main
- Same `.venv` for both runs (verified `pyproject.toml` and `poetry.lock` unchanged across `59908b7..1fd0960`)

### Numbers
| State | Errors | Files | Source files checked |
|-------|--------|-------|----------------------|
| PRE   | 10     | 5     | 271                  |
| POST  | 10     | 5     | 272                  |

The `+1` source-file count matches Phase 0's net (`+2` new constants modules, `−1` deleted `src/config/__init__.py`).

### Gate result
Sorted error lines from PRE and POST diff to **zero** lines. No Phase 0-touched file appears in the post-set; the 10 surviving errors are all in untouched code (`bot/handlers/{advertiser,owner}/*`, `core/services/{analytics,mediakit}_service.py`, `tasks/ord_tasks.py`).

### Verdict
**CLEAN — Phase 1 is not blocked by Phase 0 typecheck regressions.**

Baseline frozen at: **10 errors / 5 files / 272 src files** as of commit `1fd0960`. Any new error in this set going forward = blocker.

### Artifacts
- `reports/docs-architect/discovery/typecheck_baseline.md` (the canonical record)
- `reports/docs-architect/discovery/mypy_baseline_pre_phase0.txt` (raw mypy output, parent commit)
- `reports/docs-architect/discovery/mypy_baseline_post_phase0.txt` (raw mypy output, current main)

**Pathing note:** the user spec said `reports/docs-architect/typecheck_baseline.md`, but that directory's top level is `.gitignored` (`reports/docs-architect/*`). A baseline placed there does not survive `git checkout`. I moved the file into `discovery/` (which is tracked) so the baseline is reproducible across clones. Mention if the original path is required for some external tooling — easy to add a tracked symlink or duplicate.

### Caveat
`make typecheck` runs `mypy src/` only — it does NOT typecheck `tests/`. The three Phase 0 test files (`tests/unit/api/test_jwt_aud_claim.py`, `tests/unit/api/test_jwt_rate_limit.py`, `tests/unit/test_contract_schemas.py`) are out of scope of this baseline by configuration. Mentioned for transparency; consistent with how the gate was specified.

---

## PF.2 — 401 vs 426 for aud-less legacy tokens

### Axis A — semantic reasoning

**401 — case for it:** The token is cryptographically valid. Failing claim validation is arguably a credential defect ("you presented a credential, it's incomplete/wrong"). RFC 7235 §3.1 ascribes "missing or invalid credentials" to 401. Phase 0 already chose 401, with the rationale that a one-time re-login is acceptable in pre-prod.

**426 — case for it:** RFC 7231 §6.5.15 defines 426 for "client should switch to a different protocol." An aud-less token is a *legacy protocol version* — it pre-dates a now-mandatory claim. 426 communicates this precisely. The currently merged plan (`IMPLEMENTATION_PLAN_ACTIVE.md` §1.B.1) explicitly calls for 426; Phase 0's 401 is the deviation.

**Tilt:** 426 is more semantically faithful, but only by a small margin in real terms. The decisive axis is B.

### Axis B — are there active legacy-token holders?

| Source | Status | Finding |
|---|---|---|
| DB user counts (`docker compose exec db psql`) | Available | **0 total users**; 0 active in 24h. Pre-prod state confirmed. |
| Redis active sessions/tickets (`docker compose exec redis redis-cli`) | Available | **0 keys** matching `auth:*`, `ticket:*`, `session:*`. Bridge has not been exercised on real traffic. |
| API logs (`docker compose logs api --tail=5000`) | Available | **No aud-rejection events** logged. The 401 path on aud-less tokens has never fired against actual users. |
| Phase 0 deploy timestamp | Available | Live since `~03:43 UTC 2026-04-25` (≈ 5h ago at time of research). |

**There are no active legacy-token holders in the wild.** The system is genuinely pre-production with zero real users. The choice between 401 and 426 has no behavioral impact today — it's purely a signal-correctness question.

### Recommendation
**Flip to 426 in Phase 1, first commit.** Rationale:
1. Cost is trivial: one line in `src/api/dependencies.py:67` (`HTTP_401_UNAUTHORIZED` → `HTTP_426_UPGRADE_REQUIRED`) plus one line in `tests/unit/api/test_jwt_aud_claim.py::test_case3_*` (assertion `== 401` → `== 426`).
2. Aligns with the merged plan; closes a documentation/code drift before it ossifies.
3. Establishes the precedent for clients (mini_app, web_portal, future SDKs) to handle 426 = "your session format is obsolete, re-authenticate" — a clearer signal than 401 = "your token is wrong" (which has many other causes).
4. Pre-prod = no users = no rollout risk.

### Objection raised in passing
**Bug found while researching:** `src/api/dependencies.py:64-69` (the aud-less rejection branch) does **not** include `WWW-Authenticate: Bearer` header, but the parallel branch at line 44-49 (missing-credentials) does. RFC 7235 §3.1 says 401 SHOULD include `WWW-Authenticate`. If we flip to 426 the header isn't strictly required, but adding it (or its 426 equivalent) is good practice and makes the response self-describing for any client that walks the standard. Suggest including this in the first Phase 1 commit alongside the status-code flip.

### Decision required
- [ ] **Approve 426 flip (with WWW-Authenticate header added) as Phase 1 first commit**
- [ ] Keep 401 — accept plan/code drift, document the deviation in plan

---

## PF.3 — bridge happy-path end-to-end test

### What was missing
Phase 0 acceptance suite (`tests/unit/api/test_jwt_aud_claim.py` case 5) verifies the bridge endpoints return the expected response shape. It does NOT verify that the resulting `access_token` is actually accepted by the auth dependency. The unit-test infrastructure stops at "consume returns AuthTokenResponse with `source=web_portal`."

### What was added
`tests/integration/test_ticket_bridge_e2e.py` — single test, four steps:

1. Mint a valid `aud="mini_app"` JWT for a fake user.
2. `POST /api/auth/exchange-miniapp-to-portal` → 200, ticket payload returned.
3. `POST /api/auth/consume-ticket` → 200, `access_token` with `source=web_portal`.
4. **Feed the access_token into `get_current_user`** → returns the same user. *(This is the gap relative to case 5.)*

### Result
```
============================== 1 passed in 5.29s ===============================
```

### Stand-related note (mild objection)
The user's PF.3 spec said "Стенд: локальный docker compose; `docker compose exec api pytest tests/integration/test_ticket_bridge_e2e.py -v`." This is **not directly runnable** with the current infrastructure:
- The `api` Dockerfile only `COPY src/`; `tests/` is not in the image and not bind-mounted.
- The `api` container has no `/var/run/docker.sock`, so `testcontainers` (used by other integration tests) cannot spin up its isolated Postgres from inside.

I therefore ran the test on the host via `poetry run pytest tests/integration/test_ticket_bridge_e2e.py -v` (same `.venv`, same code, just a different process boundary). This is functionally equivalent and is how the existing `tests/integration/*` suite is run today — no integration test in this repo runs via `docker compose exec api`.

If you want true "docker compose exec api pytest" to be the canonical path, that's a separate hardening task (mount `tests/` and `pyproject.toml` into the container, or COPY them into a dev/test image stage). Not blocking Phase 1; flag for backlog.

### Verdict
**PASS — bridge happy-path verified, Phase 1 not blocked.**

### Artifact
- `tests/integration/test_ticket_bridge_e2e.py` — 1 test, ASGI in-process, FakeRedis stub (consistent with case 5's pattern), real `get_current_user` dep at step 4.

---

## PF.4 — audit middleware: refactor in place vs parallel file

### File metrics
- `src/api/middleware/audit_middleware.py`: **104 LOC total** (76 executable, 18 blank, 5 comment, 4 docstring)
- Single helper `_extract_user_id_from_token` (~23 LOC, lines 34-56)
- Single class `AuditMiddleware.dispatch` (~31 LOC, lines 59-93)

### Wiring
- Registered in `src/api/main.py:169` via `app.add_middleware(AuditMiddleware)`.
- FastAPI middleware order is LIFO: `CORSMiddleware` (outermost) → `AuditMiddleware` → route handlers.
- `dispatch` calls `await call_next(request)` first; the auth dependency has fully executed by the time control returns. `request.state` is shared with route execution, so anything written by a dependency is visible to the middleware afterwards.

### Critical insight
The FIXME suggests reading user from `request.state.user_id`, but **`request.state` is not currently written** — `_resolve_user_for_audience` (in `src/api/dependencies.py`) returns the User object via DI but does not mutate state. So the fix has two parts, not one.

### Fix sketch — LOC estimate
| Step | File | Net LOC |
|------|------|---------|
| 1. Delete `_extract_user_id_from_token` helper | `audit_middleware.py` | −23 |
| 2. Replace `_extract_user_id_from_token(...)` call with `getattr(request.state, "user_id", None)` | `audit_middleware.py` | net −1 |
| 3. Append `request.state.user_id = user.id` before `return user` in `_resolve_user_for_audience` | `dependencies.py` | +1 |
| 4. (Optional) Add a unit test for AuditMiddleware that pokes `request.state` directly | `tests/unit/...` | +20 if added |

**Net: ≈ 21 LOC across 2 files** (excluding optional test). Well under the 50-LOC / 1-file threshold even with the test.

### Hidden risks
- **No existing tests for `AuditMiddleware`** (`grep -rn AuditMiddleware tests/` → 0 hits). The refactor is mechanically safe but adding even a smoke test would be prudent. Not blocking.
- The `getattr(..., None)` fallback handles routes without auth gracefully — same behavior as today (`_extract_user_id_from_token` returns `None` on missing/malformed `Authorization`).
- No external callers of `_extract_user_id_from_token` (`grep -rn _extract_user_id_from_token src/` → only the middleware).

### Recommendation
**Refactor in place during Phase 1 §1.B.0** (before any new logic). The change is small, mechanical, eliminates a "JWT decoded without signature verification" code smell, and the parallel-file approach proposed in the plan would leave the FIXME indefinitely — which is exactly the kind of "TODO ticket that becomes permanent" the plan's review is supposed to prevent.

### Decision required
- [ ] **Approve refactor in §1.B.0** (≈ 21 LOC, 2 files: `audit_middleware.py` + `dependencies.py`)
- [ ] Keep parallel-file approach + Phase 2 TODO ticket (text drafted by the agent — available on request)

---

## Cross-cutting observations

1. **WWW-Authenticate inconsistency** in `dependencies.py:44-49` vs `64-69` — the missing-header branch sets it, the missing-aud branch doesn't. Best fixed alongside the 401→426 flip.

2. **Test infrastructure gap (low-priority).** Existing `tests/integration/*` runs on the host with poetry, not inside `api`. Either accept that as canonical or invest in a dev/test container image with `tests/` baked in. Not a Phase 1 prerequisite; logging it for backlog.

3. **Phase 0 surface is unusually clean.** Both PF.1 and PF.3 returned trivially clean verdicts; only PF.2 surfaced an actual decision-worthy gap (and it's small). The Phase 0 acceptance suite + objections-section discipline appear to have been effective at catching most issues during the phase rather than after.

---

## Decisions required before Phase 1 starts

1. **PF.2:** approve **426** flip as Phase 1's first commit, with `WWW-Authenticate` header added? *(or keep 401 and document the drift)*
2. **PF.4:** approve **refactor of `audit_middleware.py`** (≈ 21 LOC, 2 files) inside Phase 1 §1.B.0 as the very first chunk of code? *(or keep parallel-file approach + Phase 2 ticket)*
3. **PF.3 stand:** acknowledge that "docker compose exec api pytest" is **not the runnable path today** and accept host-side `poetry run pytest` as canonical for integration tests, or file a separate hardening task to bake tests into a dev image?

Once decisions arrive I will:
- Open `feature/fz152-legal-hardening` off `develop`.
- If PF.2 = 426 and PF.4 = refactor, the first two commits of Phase 1 land those two changes (CHANGELOG breaking-fix entries flag both).
- Then the rest of Phase 1 per the existing plan (`IMPLEMENTATION_PLAN_ACTIVE.md` §1.B–§1.D).

**STOP. Nothing merged to `develop` from `chore/phase0-followup` yet — only the new test file and the three baseline artifacts are added on this branch, and they're independent of any Phase 1 decision.**

🔍 Verified against: 1fd0960fb4e99fc03646475d89e52b5f972d287d | 📅 Updated: 2026-04-25T08:34:16Z
