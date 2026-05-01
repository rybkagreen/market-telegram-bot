# BL-066 — Split bot-to-API HMAC secret из BOT_TOKEN

**Date:** 2026-05-01
**Branch:** `feat/bl-055-direct-bot-to-portal-exchange`
**Type:** `refactor(security)` — defence-in-depth, no behaviour change at runtime when secrets are correctly provisioned.

## Rationale

Before BL-066 the bot signed each `POST /api/auth/exchange-bot-token-to-portal`
request with `HMAC_SHA256(BOT_TOKEN, …)`, reusing the Telegram-API
credential as the server-to-server auth secret. Two distinct trust
boundaries shared one key:

- **Telegram side** — `BOT_TOKEN` is the credential that authenticates
  the bot to Telegram (aiogram getUpdates / sendMessage / etc.) and is
  used to verify Mini App `init_data`. Compromise of `BOT_TOKEN` here
  means an attacker speaks to Telegram as the bot.
- **Infrastructure side** — bot ↔ API HMAC was the credential that
  authenticated the bot's exchange call to the local API. Compromise
  here means an attacker mints portal-login URLs for arbitrary
  Telegram IDs.

Sharing one key linked the two compromise surfaces. Splitting them
keeps a leak in either channel from unlocking the other.

## Scope

- New required Pydantic Settings field
  `bot_api_hmac_secret` (`src/config/settings.py`), env alias
  `BOT_API_HMAC_SECRET`, no default.
- HMAC primitives in `src/api/auth_bot_hmac.py` —
  `verify_bot_request_signature` and `sign_bot_request` —
  parameter `bot_token: str` renamed to `hmac_secret: str`. Module
  docstring updated to reference `BOT_API_HMAC_SECRET` instead of
  `BOT_TOKEN`.
- Caller sites:
  `src/api/routers/auth.py:exchange_bot_token_to_portal` reads
  `settings.bot_api_hmac_secret`; `src/bot/utils/portal_deeplink.py:build_portal_deeplink`
  reads the same. `BOT_TOKEN` is no longer touched in either path.
- Tests refreshed (parameter names + Settings field references):
  `tests/unit/api/test_bot_hmac.py` (literal `BOT_TOKEN`
  variable → obviously fake `HMAC_SECRET`),
  `tests/unit/api/test_exchange_bot_token_to_portal.py`
  (`_signed_post` parameter, `test_wrong_bot_token_returns_401`
  renamed to `test_wrong_hmac_secret_returns_401`),
  `tests/unit/test_bot_portal_deeplink.py`
  (HMAC recompute reads `settings.bot_api_hmac_secret`).
- Configuration templates:
  `.env.example` and `.env.test.example` extended with
  `BOT_API_HMAC_SECRET` placeholder.
  `docker-compose.yml` not edited — every service uses
  `env_file: .env` pattern (file-level pull picks up new var).
- Documentation:
  `docs/AAA-09_DEPLOYMENT.md` Security table extended with
  `BOT_API_HMAC_SECRET` row plus `openssl rand -hex 32` recipe in
  the key-generation section.

## Affected files

- `src/config/settings.py`
- `src/api/auth_bot_hmac.py`
- `src/api/routers/auth.py`
- `src/bot/utils/portal_deeplink.py`
- `tests/unit/api/test_bot_hmac.py`
- `tests/unit/api/test_exchange_bot_token_to_portal.py`
- `tests/unit/test_bot_portal_deeplink.py`
- `.env.example`
- `.env.test.example`
- `docs/AAA-09_DEPLOYMENT.md`
- `CHANGELOG.md`
- `reports/docs-architect/discovery/CHANGES_2026-05-01_BL-066-split-bot-api-hmac-secret.md`
  (this file)

## Business logic impact

- **API contract:** unchanged. Wire format, header names, signature
  algorithm, body format, response shape — identical. Existing
  Mini App, web portal, and consumer flows untouched.
- **Bot ↔ API call shape:** unchanged.
- **Settings:** new required field — startup will fail loudly if
  `BOT_API_HMAC_SECRET` is missing from the environment. This is
  intentional (no silent fallback to `BOT_TOKEN`).

## Deployment requirement (breaking)

Production `.env` must provision `BOT_API_HMAC_SECRET` **before**
restart. There is no fallback to `BOT_TOKEN`; the API and bot will
refuse to start without the new variable.

```bash
# generate
openssl rand -hex 32

# add to .env
BOT_API_HMAC_SECRET=<value-from-above>

# restart (per CLAUDE.md "Applying Changes" rule)
docker compose up -d --build nginx api
docker compose restart bot
```

Both `bot` and `api` containers must read the **same** secret value;
otherwise HMAC verification fails and the bot's portal-deeplink
buttons silently fall back to a no-button menu render.

## Rollback

`git revert <SHA>` reverts the code change cleanly. After revert,
`BOT_API_HMAC_SECRET` becomes an unused variable in `.env` (harmless;
Pydantic Settings has `extra="ignore"`). Production rolls back to
using `BOT_TOKEN` as the HMAC key. **Note**: if `.env` was already
provisioned ahead of merge, the revert alone is enough — the unused
variable does no harm. If you also want to clean `.env`, remove the
new line manually.

## Verification (Шаг 3 + Шаг 5)

- Targeted pytest passes: `tests/unit/api/test_bot_hmac.py`,
  `tests/unit/api/test_exchange_bot_token_to_portal.py`,
  `tests/unit/test_bot_portal_deeplink.py` — see commit verify gate.
- `make ci-local` — see commit verify gate; baseline preserved.
- `rg "settings.bot_token" src/api/ src/bot/utils/portal_deeplink.py`
  returns 0 hits (the only legitimate `settings.bot_token` reads
  remain in `src/auth_utils.py` and aiogram bot init paths, none
  of which are HMAC).

🔍 Verified against: bef07b16a6ad2d32a25fe6ec706dde4bb35a918a (parent) | 📅 Updated: 2026-05-01T07:54+03:00
