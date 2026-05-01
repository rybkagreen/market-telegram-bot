---
backlog: BL-055
commit: 1/3 — API endpoint + auth helpers + JWT issuer + tests + CHANGELOG
date: 2026-05-01
branch: feat/bl-055-direct-bot-to-portal-exchange
---

# CHANGES — BL-055 Commit 1: bot-to-portal exchange endpoint

Adds `POST /api/auth/exchange-bot-token-to-portal` so the bot can mint a
portal-login URL server-side, replacing the
bot → mini_app placeholder → `/api/auth/exchange-miniapp-to-portal`
indirection.

## Affected files

| File | Type | Notes |
|---|---|---|
| `src/config/settings.py` | edited | +`internal_api_base_url`, `bot_portal_exchange_allowed_paths`, `bot_auth_timestamp_tolerance_sec`; CSV-or-JSON validator on the tuple field |
| `src/api/auth_bot_hmac.py` | NEW | `verify_bot_request_signature()` + `sign_bot_request()` — pure stdlib, constant-time compare |
| `src/api/routers/auth.py` | edited | extracted `_issue_portal_ticket()` helper (Type 1 within-scope); `exchange_miniapp_to_portal` now calls helper (no behaviour change); new `BotPortalExchangeRequest` / `BotPortalExchangeResponse` schemas; new handler `exchange_bot_token_to_portal` |
| `tests/unit/api/test_bot_hmac.py` | NEW | 12 unit tests — sign/verify round-trip, tamper, replay window, header malformation, hex casing |
| `tests/unit/api/test_exchange_bot_token_to_portal.py` | NEW | 7 ASGI tests — happy path, PII-bound payload, 401 (bad signature, missing header, wrong bot token), 400 (disallowed redirect), 404 (unknown user) |
| `CHANGELOG.md` | edited | new `### Added` block under `[Unreleased]` |
| `reports/docs-architect/discovery/BL_055_RESEARCH_2026-05-01.md` | NEW | research file (staged with this commit) |

## Business logic / contract impact

### Public contract change (FE-visible)

`POST /api/auth/exchange-bot-token-to-portal` is a new public endpoint:

```http
POST /api/auth/exchange-bot-token-to-portal HTTP/1.1
X-Bot-Auth-Timestamp: 1714521600000
X-Bot-Auth-Signature: <hex hmac-sha256>
Content-Type: application/json

{"telegram_id": 100042, "redirect_path": "/own/payouts/request"}
```

Success → `200 OK`:

```json
{"ticket_url": "https://portal.rekharbor.ru/login/ticket?ticket=<jwt>&redirect=%2Fown%2Fpayouts%2Frequest"}
```

Failures: `401` (any auth check fails — generic "Invalid bot auth"),
`400` (`redirect_path` not in whitelist), `404` (unknown
`telegram_id`).

The minted ticket payload is identical to the one issued by
`exchange-miniapp-to-portal` (`{sub, tg, plan, jti, aud="web_portal", exp, iat}`)
so the existing `consume-ticket` handler accepts both without
modification.

### Internal contract change

`auth.py::_issue_portal_ticket()` is the new single source of truth for
ticket-JWT minting. Both bridge endpoints call into it. Renaming /
re-shaping any claim now lands in one place. Behaviour for the
existing `exchange-miniapp-to-portal` is unchanged — same payload,
same Redis key format, same TTL.

### FSM impact

None — bot FSM remains unchanged (BL-055 Commit 2 will swap a sync
helper for an async deeplink mint, transparent to FSM).

### DB impact

None.

## Adaptations applied (Type 2)

- **A4 ticket payload — refined to match existing shape.** Plan-as-written
  proposed `{sub: telegram_id, exp, iat, purpose, redirect}`. Adapted to
  `{sub: str(user.id), tg, plan, jti, aud="web_portal", exp, iat}` so
  the existing `consume-ticket` handler accepts it. Redirect target
  travels as a URL query parameter, not a JWT claim. See
  `BL_055_RESEARCH_2026-05-01.md` § O.1.
- **A10 internal API base URL.** Added `internal_api_base_url` Setting
  (default `http://api:8001`) so the bot reaches the API through Docker
  DNS, not through public nginx/Cloudflare. See research § O.3.

## Adjacent improvements (Type 1)

- `auth.py` — extracted ~30 LOC of inline ticket-issuance into
  `_issue_portal_ticket()` to remove duplication between the two bridge
  endpoints. Bounded to `auth.py`, no semantic change to the existing
  endpoint. Necessary for clean reuse, not optional cleanup.
- `auth_bot_hmac.py` exposes a `sign_bot_request()` companion to
  `verify_bot_request_signature()` so the bot helper (Commit 2) and the
  test suite share one wire-format definition. Avoids
  silent-format-drift between signer and verifier.

## Within-commit skips (Type 3)

None — every test in the agreed plan landed.

## Verify gate

| Check | Result |
|---|---|
| `ruff check src/ tests/` | 20 errors (baseline preserved — all in pre-existing files outside this commit) |
| `ruff format --check src/ tests/` | 371 files clean |
| `pytest tests/unit/api/test_bot_hmac.py` | 12 passed |
| `pytest tests/unit/api/test_exchange_bot_token_to_portal.py` | 7 passed |
| `pytest tests/unit/api/test_jwt_aud_claim.py tests/integration/test_ticket_bridge_e2e.py` | 12 passed (existing ticket-bridge regression — no drift after `_issue_portal_ticket()` extraction) |
| `pytest tests/unit/test_contract_schemas.py` | 22 passed (no FE-facing schema rename — `TicketResponse` snapshot intact; new schemas not yet pinned, follow-up if needed) |
| OpenAPI surface | `BotPortalExchangeRequest` / `BotPortalExchangeResponse` available under `components.schemas` once API restarts |

🔍 Verified against: feat/bl-055 HEAD pre-commit
📅 Updated: 2026-05-01
