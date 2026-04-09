# Changes: Landing Phase 1 — Init & Config
**Date:** 2026-04-08T20:30:00Z
**Author:** Claude Code
**Sprint/Task:** Landing Phase 1 — Init & Config

## Affected Files (new)
- `landing/package.json` — зависимости проекта (React 19, TS 6.0.2, Vite 8, Tailwind 4, @vitejs/plugin-react ^6.0.0 — требует Vite 8)
- `landing/tsconfig.json` — TS 6.0.2 конфиг (types:["node"], moduleResolution:bundler, skipLibCheck:true)
- `landing/vite.config.ts` — сборщик с @tailwindcss/vite plugin; manualChunks как функция (rolldown Vite 8 требует Function, не Object)
- `landing/src/index.css` — Tailwind @theme с полными токенами из DESIGN.md
- `landing/src/vite-env.d.ts` — `/// <reference types="vite/client" />` (TS 6 требует для CSS side-effect imports)
- `landing/index.html` — SEO meta, preconnect fonts, OG, Twitter Card, JSON-LD (5 типов: WebSite/Organization/Service/BreadcrumbList + FAQPage placeholder)
- `landing/src/main.tsx` — точка входа React с BrowserRouter
- `landing/src/App.tsx` — роутинг (/, /privacy)
- `landing/src/components/Header.tsx` — заглушка (Phase 2: full nav)
- `landing/src/components/Hero.tsx` — заглушка (Phase 2: full hero)
- `landing/src/components/Footer.tsx` — заглушка (Phase 2)
- `landing/src/screens/Privacy.tsx` — заглушка (Phase 4: 152-ФЗ)
- `landing/src/lib/constants.ts` — тарифы Free/299/990/2999, форматы, SITE_URL/BOT_URL/PORTAL_URL (sync с tariffs.py)
- `landing/src/lib/seo.ts` — buildFAQJsonLd() builder
- `landing/scripts/generate-sitemap.ts` — prebuild sitemap генерация → public/sitemap.xml
- `landing/public/robots.txt` — robots + Crawl-delay:1 для Яндекс
- `landing/lighthouserc.js` — пороги Lighthouse CI (Performance ≥90, SEO 100, A11y ≥95)
- `landing/nginx.conf` — Nginx конфиг внутри Docker-контейнера (gzip, cache headers, SPA fallback)
- `landing/Dockerfile` — multi-stage: node:22-alpine builder + nginx:1.27-alpine serve
- `.claude/settings.json` — hooks (PostToolUse ESLint, Stop warning, PreToolUse force-push guard)
- `.claude/skills/docs-sync/SKILL.md` — skill документации
- `.claude/skills/landing-dev/SKILL.md` — skill лендинга с полным design system
- `CLAUDE.md` — append: Documentation & Changelog Sync section + NEVER TOUCH extensions + Landing-specific rules

## Fixes Applied During Init
1. `@vitejs/plugin-react` bumped `^4.0.0` → `^6.0.0` (v4 не поддерживает Vite 8 peer deps)
2. `vite.config.ts` `manualChunks` изменён с Object на Function (rolldown в Vite 8 требует Function)
3. `src/vite-env.d.ts` добавлен для TS 6.0.2 (CSS side-effect import требует vite/client types)

## Business Logic Impact
Создан полный скаффолд лендинга. Тарифы в constants.ts синхронизированы вручную с
src/constants/tariffs.py (Free/299/990/2999). Лендинг полностью статический —
нет runtime-зависимости от FastAPI.

## Verification
- `npx tsc --noEmit` → 0 errors
- `npm run build` → dist/ содержит index.html + assets/ (259ms)
- `npm run dev` + curl → HTTP 200 на localhost:5175
- `public/sitemap.xml` → содержит `<urlset>` с / и /privacy

## API / FSM / DB Contracts
Нет — лендинг статический.

## Migration Notes
Нет.

---
🔍 Verified against: cf0e7de | 📅 Updated: 2026-04-08T20:30:00Z
