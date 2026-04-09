# Hotfix: CSP блокировал Google Fonts
**Date:** 2026-04-09T10:11:00Z
**Author:** Claude Code
**Type:** Hotfix (не прерывает Phase 4+6)

## Root Cause
`security_headers_landing.conf`: `style-src 'self'` блокировал загрузку
CSS-файла Google Fonts с `fonts.googleapis.com`. Шрифты Outfit/DM Sans/Poppins/Roboto
не загружались, браузер использовал системный fallback.

## Fix
`style-src 'self' https://fonts.googleapis.com` — добавлен origin для Google Fonts CSS.
`font-src` уже содержал `https://fonts.gstatic.com` (файлы шрифтов).
`connect-src` расширен: добавлены `https://fonts.googleapis.com https://fonts.gstatic.com`.

## Affected Files
- `nginx/conf.d/security_headers_landing.conf` — исправлен style-src, расширен connect-src

## Applied
Через `docker cp` + `nginx -s reload` (без пересборки образа).
При следующей полной пересборке `docker compose build nginx` изменение войдёт автоматически.

## Verified
```
content-security-policy: default-src 'self'; script-src 'self';
  style-src 'self' https://fonts.googleapis.com;
  font-src 'self' https://fonts.gstatic.com;
  img-src 'self' data: https:;
  connect-src 'self' https://fonts.googleapis.com https://fonts.gstatic.com;
  frame-ancestors 'none';
```

---
🔍 Verified against: 085d306 | 📅 Updated: 2026-04-09T10:11:00Z
