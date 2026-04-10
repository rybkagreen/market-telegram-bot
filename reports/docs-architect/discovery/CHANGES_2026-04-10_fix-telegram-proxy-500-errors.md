# Changes: fix-telegram-proxy-500-errors

**Date:** 2026-04-10T10:07:00+00:00
**Author:** Qwen Code
**Sprint/Task:** S-29B Hotfix — /api/channels 500 + bot crash-loop (Telegram proxy)

## Affected Files
- `src/bot/main.py` — refactored Bot creation: deferred to async `_create_bot()` function; configures `AiohttpSession(proxy=settings.telegram_proxy)` inside the event loop (module-level `Bot()` was causing event-loop-less `ProxyConnector` crash)
- `src/api/dependencies.py` — `get_bot()` singleton already supported `HTTPXRequest(proxy=...)` (no changes needed, verified working)
- `src/api/main.py` — added `close_bot()` to lifespan shutdown (from previous hotfix)
- `pyproject.toml` — changed `httpx = "^0.28.1"` → `httpx = {extras = ["socks"], version = "^0.28.1"}` (added `socksio` dependency)
- `poetry.lock` — regenerated
- `.env` — added `TELEGRAM_PROXY=socks5://172.18.0.1:1080`
- `src/config/settings.py` — `telegram_proxy: str | None = None` (already present, no changes)
- `/etc/systemd/system/socat-telegram-proxy.service` — new systemd service for socat relay

## Business Logic Impact
- **No functional changes** to business logic. Both bot and API now route all Telegram API calls through the xray SOCKS5 proxy (127.0.0.1:1080) via socat relay (172.18.0.1:1080).
- Fixes `/api/channels/check` 500 errors (was timing out on `bot.get_chat()`)
- Fixes bot container crash-loop (was `RuntimeError: no running event loop` → then `TelegramNetworkError: Request timeout error`)
- Fixes "Unclosed client session" errors every ~6 minutes

## Root Cause
Docker containers cannot reach `api.telegram.org` directly (firewall blocks outbound to Telegram IPs from container network). The host machine has an xray SOCKS5 proxy on 127.0.0.1:1080, but containers can't reach 127.0.0.1. Solution: socat relay on Docker gateway (172.18.0.1:1080) → 127.0.0.1:1080, with both libraries configured to use `socks5://172.18.0.1:1080`.

## Infrastructure Changes
- **socat systemd service**: `/etc/systemd/system/socat-telegram-proxy.service` — auto-starts on boot, restarts on failure
- **Docker gateway IP**: 172.18.0.1 (network: `market-telegram-bot_market_bot_network`)
- **Proxy URL**: `socks5://172.18.0.1:1080` (stored in `.env` as `TELEGRAM_PROXY`)

## Migration Notes
- No DB migrations required
- `.env` must contain `TELEGRAM_PROXY=socks5://172.18.0.1:1080`
- socat systemd service must be enabled: `systemctl enable socat-telegram-proxy`

## Verified Against
- Bot: authenticated as @RekharborBot, polling started
- API: `GET /api/channels/stats` → 200 OK
- Proxy: `httpx` through SOCKS5 → 200 on `getMe`
- `alembic check`: clean (from previous hotfix)
