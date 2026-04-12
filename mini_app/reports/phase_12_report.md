# Phase 12: Docker + Nginx деплой

**Дата:** 2026-03-16
**Статус:** ✅ Завершено

## Что сделано

- [x] `nginx/conf.d/default.conf`: разделён на два HTTPS server block-а (app.rekharbor.ru + rekharbor.ru)
- [x] `app.rekharbor.ru`: Mini App на root `/`, CSP `frame-ancestors` для Telegram, без X-Frame-Options
- [x] `rekharbor.ru`: placeholder страница + API + Flower + webhooks, X-Frame-Options SAMEORIGIN + HSTS
- [x] `nginx/conf.d/security_headers_app.conf` и `security_headers_main.conf` — сниппеты для хедеров (fix nginx inheritance issue)
- [x] `docker/Dockerfile.nginx`: HEALTHCHECK обновлён с `/app/` на `/health`; сниппеты скопированы в образ
- [x] `mini_app/vite.config.ts`: `base = '/'` (не было `/app/` — уже было правильно)
- [x] `docker compose build nginx` — успешно (React build 518ms)
- [x] `docker compose up -d nginx` — успешно

## Проверки

- [x] `https://app.rekharbor.ru/` → Mini App HTML (200) ✅
- [x] `https://app.rekharbor.ru/health` → `healthy` (200) ✅
- [x] `https://app.rekharbor.ru/api/docs` → FastAPI docs (200) ✅
- [x] `https://rekharbor.ru/` → placeholder страница (200) ✅
- [x] `https://rekharbor.ru/health` → `healthy` (200) ✅
- [ ] `https://rekharbor.ru/flower/` — не тестировалось (Flower запущен)
- [x] CSP header на `app.rekharbor.ru` содержит `frame-ancestors` telegram ✅
- [x] X-Frame-Options **НЕТ** на `app.rekharbor.ru` ✅
- [x] X-Frame-Options SAMEORIGIN на `rekharbor.ru` ✅
- [x] HSTS на `rekharbor.ru` ✅
- [x] Все Docker контейнеры Up (10/10) ✅
- [ ] Бот отвечает в Telegram — не тестировалось
- [ ] Mini App открывается в Telegram — требует настройки Menu Button в BotFather

## Security headers

```
app.rekharbor.ru:
  content-security-policy: frame-ancestors 'self' https://web.telegram.org https://*.telegram.org
  x-content-type-options: nosniff
  x-xss-protection: 1; mode=block
  (NO X-Frame-Options) ✅
  (NO HSTS)

rekharbor.ru:
  x-frame-options: SAMEORIGIN
  x-content-type-options: nosniff
  x-xss-protection: 1; mode=block
  strict-transport-security: max-age=31536000; includeSubDomains
```

## Решённые проблемы

**nginx `add_header` inheritance issue**: В nginx `add_header` на уровне server-block не наследуется в location-блоках, у которых есть свои `add_header`. Решение: вынесли security headers в два отдельных include-сниппета (`security_headers_app.conf`, `security_headers_main.conf`) и подключили их через `include` в каждом location.

## Следующий шаг

Настроить Menu Button в BotFather:
1. `/mybots` → @RekharborBot
2. Bot Settings → Menu Button → Configure menu button
3. URL: `https://app.rekharbor.ru/`
4. Title: `Открыть`

## 🎉 ПРОЕКТ ЗАВЕРШЁН

Все 12 фаз выполнены. Mini App полностью развёрнут и доступен по HTTPS.

### Итоговая статистика проекта
- Экранов: 31
- UI компонентов: 22
- CSS modules: ~55
- API хуков (TanStack Query): ~26
- TypeScript типов: 24
- Design tokens: 97 CSS переменных
- Build time: ~518ms
- Bundle size: ~185kB (main) + 31 lazy chunks
- nginx: 2 server block-а, gzip, 1y asset cache, CSP для Telegram iframe
