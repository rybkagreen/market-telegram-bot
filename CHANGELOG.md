# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- INSTRUCTIONS.md — developer instructions with critical documentation rule, agent routing, skills system
- Documentation cross-reference system: QWEN.md ↔ INSTRUCTIONS.md ↔ CHANGELOG.md ↔ README.md
- `landing/Header`: sticky с backdrop-blur, ScrollSpy nav pills, mobile hamburger drawer (motion/react)
- `landing/Hero`: H1 Outfit clamp(2.5rem,6vw,5rem), motion stagger-анимация, stats-плитки, prefers-reduced-motion
- `landing/Footer`: multi-column тёмный, реквизиты ООО «АЛГОРИТМИК АРТС», 152-ФЗ ссылки /privacy
- `landing/CookieBanner`: 152-ФЗ consent banner, localStorage persistence, AnimatePresence
- `landing/useScrollSpy`: хук активной секции по scroll event
- `landing/useConsent`: хук управления cookie-согласием (pending/accepted/declined)
- Landing page scaffold at `landing/` (Phase 1): React 19, TS 6.0.2, Vite 8, Tailwind 4.1
- `landing/src/lib/constants.ts`: tariff constants synced with backend (`tariffs.py`)
- `landing/index.html`: full SEO setup (5 JSON-LD types: WebSite/Organization/Service/BreadcrumbList + FAQPage, OG, Twitter Card)
- `landing/scripts/generate-sitemap.ts`: prebuild sitemap generator → `public/sitemap.xml`
- `landing/lighthouserc.js`: Lighthouse CI gates (Performance ≥90, SEO 100, A11y ≥95)
- `landing/Dockerfile`: multi-stage nginx build (node:22-alpine builder + nginx:1.27-alpine serve)
- `landing/nginx.conf`: gzip, immutable cache headers, SPA fallback
- Claude Code self-configuration: `.claude/settings.json` hooks (PostToolUse ESLint, Stop warning, PreToolUse force-push guard)

### Changed
- README.md: restructured from 1242 → 373 lines (70% reduction), removed duplicate sections, file trees, DB schemas

### Fixed
- ` @vitejs/plugin-react` bumped ^4→^6 (v4 lacks Vite 8 peer dep support)
- `vite.config.ts` manualChunks converted Object→Function (rolldown/Vite 8 requirement)
- `landing/src/vite-env.d.ts` added (TS 6.0.2 requires vite/client ref for CSS side-effect imports)

### mini_app — TypeScript 6.0 + TailwindCSS 4.1 Alignment
- TypeScript: ^5.9.3 → ^6.0.2 (aligned with web_portal)
- Added TailwindCSS ^4.1.0 + @tailwindcss/vite ^4.1.0 (greenfield integration, not migration)
- typescript-eslint: ^8.56.1 → ^8.58.0 (TS 6.0 peer dependency compatibility)
- tsconfig.app.json: target ES2023 → ES2025 (aligned with TS 6.0 default + web_portal)
- tsconfig.node.json: added `rootDir: "./"` (TS 6.0 rootDir default shift safeguard)
- vite.config.ts: added @tailwindcss/vite plugin integration
- src/styles/globals.css: added ` @import 'tailwindcss';` directive
- Verified: 0 tsc errors, 0 build warnings, 0 eslint warnings

## [v4.4] - 2026-04-08

### Added
- Rate limiting (10/hour) to `/api/auth/login-code` — brute-force protection
- Shared `RedisClient` dependency with connection pooling in `dependencies.py`
- CORS restrict methods/headers configuration
- `# noqa: S1172` to 6 stub methods in `stub_ord_provider.py` (protocol implementation)
- `# noqa: F401,F403,S2208` to Alembic `env.py` wildcard import (standard pattern)
- SonarQube config expanded: src + mini_app + web_portal (580 files scanned)
- Migration `t1u2v3w4x5y6` — added missing `language_code` column to `users` table

### Changed
- Billing prices: 299/999/2999 → 490/1490/4990 (from settings, not hardcoded)
- Redis connection: per-request pool → shared pool in dependencies.py
- Webhook error handling: bare except Exception → specific exceptions + retry
- SonarQube config: mini_app only → src + mini_app + web_portal

### Fixed
- Telegram widget 500 error: column language_code missing (migration t1u2v3w4x5y6)
- **billing.py** hardcoded prices (299/999/2999 → 490/1490/4990 from settings)
- Redis connection leak in login-code (per-request `aclose()` → shared connection pool)
- **is_active** check added to Login Widget auth — banned users cannot obtain JWT
- **AdminDashboard.tsx** — table missing `<thead>`/`<th scope="row">` for accessibility (S5256)
- 9× keyboard listener issues (S1082) — added `onKeyDown`, `tabIndex`, `role="button"`:
  - `Modal.tsx`, `Checkbox.tsx`, `ChannelCard.tsx`, `OwnChannels.tsx`, `ContractList.tsx`,
    `DocumentUpload.tsx`, `AdminDisputesList.tsx`, `PortalShell.tsx`
- **LegalProfileSetup.tsx** redundant ternary (S3923) — simplified 4-branch to 3-branch
- 6× unused parameters in notification wrappers — prefixed with `_` (S1172)
- 4× commented-out dead code (S125) removed from payout_service.py, billing_service.py, audit_log.py

### Code Quality
- Backend: ~70 issues fixed (unused params, dead code, noqa annotations)
- Frontend: 204 SonarQube issues identified, 11 BUG issues fixed
- Identified remaining: 75× nested ternary (S3358), 40× missing form labels (S6853), 75× `<div onClick>` → `<button>` (S7773)

### Migration Notes
```bash
alembic upgrade head
ruff check src/ --fix && ruff format src/
mypy src/ --ignore-missing-imports
```

## [v4.3.1] - 2026-04-02

### Documentation
- Updated README.md with v4.3 features (legal profiles, ORD, audit, referrals)
- Updated QWEN.md with new database models and environment variables
- Added "Что нового в v4.3" section to README.md
- Updated Tech Stack section (GlitchTip, SonarQube, Gitleaks)
- Updated Project Structure (20+ new models, services, routers)

## [v4.3] - 2026-03-14

### Added
- Feedback system: full user → admin → response flow
- Admin panel Mini App: 7 screens, 9 endpoints
- Legal profiles: LegalProfile + Contract models
- ORD registration: OrdRegistration for advertising compliance
- Audit log: AuditLog + Audit Middleware for security tracking
- Field encryption: PII encryption for sensitive data
- Referral program: ReferralStats tracking
- Video support: VideoUploader in campaigns
- Link tracking: ClickTracking for campaign links
- GlitchTip + SonarQube + Gitleaks integration
- 101 tests (all passing)
- 20+ documentation reports

### Changed
- Payouts: CryptoBot API → manual via admin panel
- B2B packages: removed
- ESCROW-001: release_escrow() ONLY after post deletion (not on publication)
- FSM States: 5 files + 2 middleware completed
- Ruff SIM102/SIM103: fixed
- is_banned: replaced with is_active
- Admin panel 404: added is_admin check in dependencies.py

### Removed
- CryptoBot service (manual payouts only)
- B2B button in main_menu
- NPD_TAX_RATE (replaced with PLATFORM_TAX_RATE)
- Bonus packages

### Breaking
- Payout workflow now manual (no CryptoBot automation)
- ESCROW release timing changed (after deletion, not publication)

### Migration Notes
```bash
alembic upgrade head
ruff check src/ --fix && ruff format src/
pytest tests/ -v
```

## [v4.2] - 2026-03-18

### Changed
- PLATFORM_COMMISSION: 0.20 → 0.15
- OWNER_SHARE: 0.80 → 0.85
- Tariff prices: 299/999/2999 → 490/1490/4990
- MIN_TOPUP: 100 → 500
- MIN_PRICE_PER_POST: 100 → 1000
- MIN_PAYOUT: 500 → 1000
- Added MIN_CAMPAIGN_BUDGET: 2000

### Added
- 5 publication formats with multipliers
- Self-dealing prevention in placement requests
- Velocity check for payouts (MVP)
- PayoutRequest: gross/fee/net breakdown
- Platform tax rate: 6% (USN)
- Payout fee rate: 1.5%

### Removed
- NPD_TAX_RATE (replaced with PLATFORM_TAX_RATE)
- Bonus packages

### Migration Notes
```bash
alembic upgrade head
ruff check src/ --fix && ruff format src/
```
