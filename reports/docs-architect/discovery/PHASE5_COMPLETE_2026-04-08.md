# Phase 5 — Landing Docker + Nginx Infrastructure: COMPLETE ✅

**Date:** 2026-04-08T21:30Z
**Author:** Claude Code
**Sprint/Task:** Landing Phase 5 — Infra

---

## Summary

Лендинг интегрирован в существующую Docker+Nginx инфраструктуру. Web portal переехал на `portal.rekharbor.ru`.

## Changes Made

| # | Change | Status |
|---|--------|--------|
| 1 | Удалены `landing/Dockerfile` и `landing/nginx.conf` | ✅ |
| 2 | Обновлён `docker/Dockerfile.nginx` — добавлен Stage 3 builder-landing | ✅ |
| 3 | Создан `nginx/conf.d/security_headers_landing.conf` — строгий CSP | ✅ |
| 4 | Обновлён `nginx/conf.d/default.conf` — 3 server block-а | ✅ |
| 5 | Certbot: расширен SSL на `portal.rekharbor.ru` | ✅ |
| 6 | DNS: A-запись `portal.rekharbor.ru` → 37.252.21.175 | ✅ |
| 7 | Пересобран и развёрнут nginx-контейнер | ✅ |
| 8 | Host nginx (`/etc/nginx/sites-enabled/rekharbor.ru`) — добавлен portal.rekharbor.ru | ✅ |
| 9 | `docker-compose.yml` — убран /etc/letsencrypt bind mount (certs baked into image) | ✅ |
| 10 | Создана `ssl_certs/` директория для baked-in сертификатов | ✅ |

## Verification Results

| Check | Result |
|-------|--------|
| `https://rekharbor.ru/` → 200 (лендинг) | ✅ |
| `https://portal.rekharbor.ru/` → 200 (портал) | ✅ |
| `https://app.rekharbor.ru/` → 200 (mini app) | ✅ |
| `https://www.rekharbor.ru/` → 301 → HTTPS | ✅ |
| Landing security headers: CSP без unsafe-inline | ✅ |
| Portal X-Robots-Tag: noindex, nofollow | ✅ |
| SSL cert: portal.rekharbor.ru in SAN | ✅ (expires Jul 7 2026) |
| Telegram Login Widget: работает | ✅ (после /setdomain portal.rekharbor.ru) |
| Docker healthcheck: healthy | ✅ |

## Architecture Notes

### Two-Layer Nginx
Проект использует двухуровневую архитектуру:
- **Host nginx** (`/etc/nginx/sites-enabled/rekharbor.ru`) — SSL терминатор (порты 80/443)
- **Docker nginx** (`docker/Dockerfile.nginx`) — внутренний прокси (127.0.0.1:8443)

При продлении SSL через certbot:
```bash
cp /etc/letsencrypt/live/rekharbor.ru/fullchain.pem ssl_certs/
cp /etc/letsencrypt/live/rekharbor.ru/privkey.pem ssl_certs/
docker compose build nginx && docker compose up -d --force-recreate nginx
nginx -s reload  # host nginx
```

## Manual Actions Pending

| # | Action | Priority |
|---|--------|----------|
| 1 | YooKassa webhook URL → `portal.rekharbor.ru/webhooks/yookassa` | HIGH |
| 2 | FastAPI ALLOWED_ORIGINS → добавить `https://portal.rekharbor.ru` | MEDIUM |
| 3 | Обновить ссылку в боте: `rekharbor.ru` → `portal.rekharbor.ru` | MEDIUM |
| 4 | Обновить canonical в web_portal | LOW |

---
🔍 Verified against: git HEAD | 📅 Updated: 2026-04-08T21:30Z
