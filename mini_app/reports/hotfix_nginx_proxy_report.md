# Hotfix: nginx proxy_pass 404

**Дата:** 2026-03-16
**Статус:** ✅ Исправлено

## Диагностика

- **FastAPI paths prefix:** все пути начинаются с `/api/` (например `/api/auth/telegram`)
- **Текущий proxy_pass:** `http://api_backend/` — С trailing slash (ошибка)
- **Внутренний тест с /api/prefix:** возвращал `400 Bad Request` (корректный ответ API)
- **Внутренний тест без /api/prefix:** возвращал `404 Not Found`
- **Корневая причина:** `location /api/ { proxy_pass http://api_backend/; }` — trailing slash в proxy_pass заставляет nginx обрезать `/api/` prefix. Запрос `/api/auth/telegram` уходил на FastAPI как `/auth/telegram` → 404. Это касалось обоих server-блоков (app.rekharbor.ru и rekharbor.ru).
- **Дополнительно:** `location /webhooks/yookassa` проксировал на `http://api_backend/webhooks/yookassa`, тогда как FastAPI endpoint находится на `/api/billing/webhooks/yookassa`.

## Исправление

**Файл:** `nginx/conf.d/default.conf`

| Блок | Строка | Было | Стало |
|---|---|---|---|
| app.rekharbor.ru `/api/` | 81 | `proxy_pass http://api_backend/;` | `proxy_pass http://api_backend;` |
| app.rekharbor.ru `/webhooks/yookassa` | 93 | `proxy_pass http://api_backend/webhooks/yookassa;` | `proxy_pass http://api_backend/api/billing/webhooks/yookassa;` |
| rekharbor.ru `/api/` | 144 | `proxy_pass http://api_backend/;` | `proxy_pass http://api_backend;` |
| rekharbor.ru `/webhooks/yookassa` | 168 | `proxy_pass http://api_backend/webhooks/yookassa;` | `proxy_pass http://api_backend/api/billing/webhooks/yookassa;` |

## Тесты после исправления

- [x] POST /api/auth/telegram через app.rekharbor.ru: **HTTP 400** (правильно — `Missing hash in initData`)
- [x] POST /api/auth/telegram через rekharbor.ru: **HTTP 400** (правильно)
- [x] GET app.rekharbor.ru/ : **HTTP 200**
- [x] GET app.rekharbor.ru/health : **healthy**
- [x] CSP header: **есть** — `frame-ancestors 'self' https://web.telegram.org https://*.telegram.org`
- [x] POST /webhooks/yookassa: **HTTP 200** (`{"status":"ok"}`)
- [x] Все контейнеры Up: **да** (10/10 контейнеров)

## Все результаты тестов (raw output)

```
=== Тест 1: POST /api/auth/telegram через app.rekharbor.ru ===
{"detail":"Invalid Telegram data: Missing hash in initData"}
HTTP 400

=== Тест 2: POST /api/auth/telegram через rekharbor.ru ===
{"detail":"Invalid Telegram data: Missing hash in initData"}
HTTP 400

=== Тест 3: GET app.rekharbor.ru/ ===
HTTP 200

=== Тест 4: Health check ===
healthy

=== Тест 5: CSP header ===
content-security-policy: frame-ancestors 'self' https://web.telegram.org https://*.telegram.org

=== Тест 6: POST /webhooks/yookassa ===
{"status":"ok"}
HTTP 200

=== Тест 7: Контейнеры ===
NAME                           STATUS
market_bot_api                 Up 2 hours
market_bot_bot                 Up 2 hours
market_bot_celery_beat         Up 4 hours
market_bot_flower              Up 3 hours
market_bot_nginx               Up About a minute (healthy)
market_bot_postgres            Up 3 hours (healthy)
market_bot_redis               Up 3 hours (healthy)
market_bot_worker_background   Up 3 hours (healthy)
market_bot_worker_critical     Up 3 hours (healthy)
market_bot_worker_game         Up 3 hours (healthy)
```
