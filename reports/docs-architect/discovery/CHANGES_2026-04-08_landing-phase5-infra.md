# Changes: Landing Phase 5 — Docker + Nginx Infrastructure
**Date:** 2026-04-08T21:13Z
**Author:** Claude Code
**Sprint/Task:** Landing Phase 5 — Infra

## Affected Files
- `docker/Dockerfile.nginx` — добавлен Этап 3: builder-landing (node:22-alpine → npm run build); Этап 4 переименован; добавлены COPY ssl_certs/ для baked-in certs
- `docker-compose.yml` — удалён volumes блок nginx (/etc/letsencrypt bind mount убран — certs baked into image)
- `nginx/conf.d/default.conf` — rekharbor.ru переключён на лендинг; добавлен portal.rekharbor.ru server block
- `nginx/conf.d/security_headers_landing.conf` — новый: строгий CSP без unsafe-inline/eval
- `ssl_certs/` — новая директория с baked-in SSL сертификатами (fullchain.pem, privkey.pem)
- `ssl_certs/` добавлен в `.gitignore`
- `/etc/nginx/sites-enabled/rekharbor.ru` (host-level) — добавлен portal.rekharbor.ru в server_name
- `landing/Dockerfile` — УДАЛЁН (не соответствовал архитектуре проекта)
- `landing/nginx.conf` — УДАЛЁН (не соответствовал архитектуре проекта)

## Architecture Note: Two-Layer Nginx
Проект использует двухуровневую архитектуру:
1. **Host nginx** (`/etc/nginx/sites-enabled/rekharbor.ru`) — SSL терминатор на портах 80/443
2. **Docker nginx** (`docker/Dockerfile.nginx`) — внутренний прокси на 127.0.0.1:8443

Host nginx получает SSL-сертификаты из `/etc/letsencrypt/` и проксирует запросы в Docker nginx.
Docker nginx содержит baked-in SSL сертификаты для внутренней маршрутизации, но внешние клиенты
видят сертификаты host nginx.

## Business Logic Impact
- rekharbor.ru теперь отдаёт лендинг (статика из /usr/share/nginx/html/landing)
- Web Portal переехал на portal.rekharbor.ru — API, Flower, webhooks работают там же
- Лендинг индексируется поисковиками; портал закрыт X-Robots-Tag: noindex, nofollow
- SSL сертификат расширен: добавлен SAN portal.rekharbor.ru (certbot --expand)
- Host nginx конфигурация обновлена: portal.rekharbor.ru добавлен в server_name

## API / FSM / DB Contracts
- YooKassa webhook URL изменился: rekharbor.ru/webhooks → portal.rekharbor.ru/webhooks
  ⚠️ Требуется обновить webhook URL в личном кабинете YooKassa
- ALLOWED_ORIGINS в FastAPI: добавить https://portal.rekharbor.ru

## Migration Notes
- Обновить ALLOWED_ORIGINS в FastAPI: добавить https://portal.rekharbor.ru
- Обновить ссылку в боте: portal.rekharbor.ru вместо rekharbor.ru
- Обновить canonical в web_portal: https://portal.rekharbor.ru
- Обновить YooKassa webhook URL в ЛК: https://portal.rekharbor.ru/webhooks/yookassa
- При продлении SSL сертификата: `cp /etc/letsencrypt/live/rekharbor.ru/fullchain.pem ssl_certs/ && cp /etc/letsencrypt/live/rekharbor.ru/privkey.pem ssl_certs/ && docker compose build nginx`

## Resolved Issues
- **Docker bind-mount SSL caching**: Docker кэшировал старые SSL-файлы при bind mount.
  Решение: baked-in сертификаты через COPY ssl_certs/ в Dockerfile + удаление volumes блока.
- **Redis AOF corruption** после restart dockerd: удалён corrupt .incr.aof файл, обновлён manifest.

---
🔍 Verified against: 085d306 | 📅 Updated: 2026-04-08T21:13Z
