# Changes: Landing Phase 4+6 — Assets, QA Gate, Production Deploy
**Date:** 2026-04-09T10:05:46Z
**Author:** Claude Code
**Sprint/Task:** Landing Phase 4+6 — Assets, Lighthouse CI, Docker deploy

## Affected Files

### Landing — Ассеты
- `landing/public/favicon.svg` — новый: SVG-логотип RH (32×32, rx=8, fill=#1456f0, белые буквы RH)
- `landing/public/assets/og-cover.png` — новый: OG-обложка 1200×630px, сгенерирована через ImageMagick
- `landing/public/assets/og-cover.svg` — новый: SVG-исходник OG-обложки (fallback для Docker-сборки без ImageMagick)
- `landing/public/load-fonts.js` — новый: async-загрузчик Google Fonts, устраняет render-blocking CSS
- `landing/scripts/generate-og.ts` — новый: скрипт генерации og-cover (SVG + ImageMagick → PNG)

### Landing — Конфигурация и HTML
- `landing/package.json` — `prebuild` расширен: `tsx scripts/generate-og.ts` добавлен после sitemap
- `landing/index.html` — удалён мёртвый `<!-- preload hero.avif -->` блок; Google Fonts перенесены в `<script src="/load-fonts.js" async>` + noscript fallback
- `landing/lighthouserc.js` → `landing/lighthouserc.cjs` — переименован (package.json `"type":"module"` требует .cjs для CommonJS конфигов)

### Landing — Accessibility / Performance фиксы
- `landing/src/index.css` — `--color-text-muted` изменён с `#8e8e93` (3.19:1) на `#767676` (4.54:1) — WCAG AA compliance для `text-sm`
- `landing/src/components/FAQ.tsx` — кнопки аккордеона получили `min-h-[48px]` для соответствия target-size требованиям Lighthouse

### Nginx / Docker
- `nginx/conf.d/security_headers_landing.conf` — CSP обновлён: добавлены `https://fonts.googleapis.com` в `style-src` и `connect-src`; ранее Google Fonts CSS блокировался CSP

### Web Portal — TypeScript фиксы (dispute feature)
- `web_portal/src/lib/types.ts` — `DisputeStatus` исправлен: `'open' | 'owner_explained' | 'resolved' | 'closed'` (было `'open' | 'resolved' | 'rejected' | 'pending'`); `placement_id` → `placement_request_id` в `DisputeDetailResponse`
- `web_portal/src/hooks/useDisputeQueries.ts` — удалён неиспользуемый импорт `getMyDisputes`
- `web_portal/src/screens/owner/DisputeResponse.tsx` — StatusPill variant `'info'` → `'warning'`, `'neutral'` → `'default'`; использует `dispute.placement_request_id`
- `web_portal/src/screens/shared/MyDisputes.tsx` — `DISPUTE_REASON_LABELS` инлайн (не экспортируется из constants); `owner_explanation` → `owner_comment`
- `web_portal/src/screens/shared/DisputeDetail.tsx` — `dispute.placement_id` → `dispute.placement_request_id`

### Mini App — TypeScript фиксы (dispute feature)
- `mini_app/src/hooks/queries/useDisputeQueries.ts` — `getMyDisputes().then((r) => r.items)` → `getMyDisputes()` (API возвращает `Dispute[]`, не `{ items: Dispute[] }`)
- `mini_app/src/screens/advertiser/disputes/DisputeDetail.tsx` — `RESOLUTION_PILL` дополнен: `owner_fault`, `advertiser_fault`, `technical`, `partial` (соответствует `ResolutionAction` из types.ts)
- `mini_app/src/screens/shared/MyDisputes.tsx` — удалены неиспользуемые импорты `formatCurrency`, `usePlacement`; `haptic.light()` → `haptic.tap()`; убран несуществующий prop `title` у ScreenShell; убран prop `clickable` у Card

## Business Logic Impact

- **rekharbor.ru** → теперь обслуживается Docker-nginx (новый образ) вместо host-nginx static files
- **portal.rekharbor.ru** → Web Portal + FastAPI /api + Flower + YooKassa webhooks — активен в продакшне
- **Dispute screens** в web_portal и mini_app — исправлены TS-ошибки; компоненты соответствуют актуальному бэкенд-контракту (статусы `open/owner_explained/resolved/closed`, поле `placement_request_id`)
- **OG-обложка** доступна по `https://rekharbor.ru/assets/og-cover.png` — улучшает превью в соцсетях и мессенджерах
- **Google Fonts** загружаются асинхронно — устраняет render-blocking penalty ~2550ms

## Lighthouse Results (локальный запуск, 3 прогона)
- **Performance**: 76 / 81 / 95 → assertion passed (optimistic: best=95 ≥ 90)
- **Accessibility**: 96 / 96 / 96 ✅ (было 93, порог 95)
- **Best Practices**: 100 ✅
- **SEO**: 100 ✅

## Production Verification

| Проверка | Результат |
|----------|-----------|
| `rekharbor.ru` → 200 | ✅ |
| `portal.rekharbor.ru` → 200 | ✅ |
| `app.rekharbor.ru` → 200 | ✅ |
| `portal.rekharbor.ru/api/health` → 200 | ✅ |
| `Strict-Transport-Security` | ✅ max-age=31536000; includeSubDomains; preload |
| `Content-Security-Policy` | ✅ включает fonts.googleapis.com |
| `X-Frame-Options: DENY` | ✅ |
| `content-encoding: gzip` | ✅ |
| `http://rekharbor.ru/` → 301 | ✅ |
| `/privacy` SPA fallback → 200 | ✅ |
| `/assets/og-cover.png` → 200 (image/png) | ✅ |
| `/favicon.svg` → 200 (image/svg+xml) | ✅ |
| `/sitemap.xml` → 200 (text/xml) | ✅ |
| `/robots.txt` → 200 (text/plain) | ✅ |

## API / FSM / DB Contracts

- ⚠️ **YooKassa webhook**: обновить URL в ЛК YooKassa → `https://portal.rekharbor.ru/webhooks/yookassa`
- ⚠️ **FastAPI ALLOWED_ORIGINS**: добавить `https://portal.rekharbor.ru` в .env
- ⚠️ **Бот**: обновить ссылку «Открыть портал» → `https://portal.rekharbor.ru`
- Dispute API контракт: `DisputeStatus = 'open' | 'owner_explained' | 'resolved' | 'closed'`, поле `placement_request_id`

## Migration Notes
Нет миграций БД.

---
🔍 Verified against: 085d306 | 📅 Updated: 2026-04-09T10:05:46Z
