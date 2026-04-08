---
name: landing-dev
description: Context and rules for working on the RekHarbor landing page at /opt/market-telegram-bot/landing/
---

# landing-dev skill

## Project location
/opt/market-telegram-bot/landing/

## Stack (exact versions)
- React 19.2+
- TypeScript 6.0.2
- Vite 8.0.0
- Tailwind CSS 4.1+ (CSS-first, @theme)
- React Router 7.x
- motion 12.x  →  import from 'motion/react'  (NOT framer-motion)
- lucide-react (latest)

## tsconfig.json requirements (TS 6.0.2 breaking changes)
```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "types": ["node"],
    "moduleResolution": "bundler",
    "module": "ESNext",
    "strict": true,
    "noEmit": true
  }
}
```
Note: `baseUrl` is deprecated in TS 6 — do not use it.

## Design system
Source of truth: DESIGN.md in /opt/market-telegram-bot/landing/
Key tokens:
- Background: #ffffff (primary), #181e25 (dark/footer)
- Text: #222222 (primary), #45515e (secondary), #8e8e93 (muted)
- Brand blue: #1456f0, hover: #2563eb
- Brand pink: #ea5ec1 — decorative only, never in text/buttons
- Border: #e5e7eb
- Shadow brand: rgba(44, 30, 116, 0.16) 0px 0px 15px
- Border radius: 8px (CTA buttons), 20-24px (product cards), 9999px (nav pills)
- Fonts: DM Sans (UI), Outfit (display), Poppins (mid-tier), Roboto (data)

## Tailwind @theme skeleton
```css
@import "tailwindcss";

@theme {
  --font-ui: "DM Sans", "Helvetica Neue", sans-serif;
  --font-display: "Outfit", "Helvetica Neue", sans-serif;
  --font-mid: "Poppins", sans-serif;
  --font-data: "Roboto", "Helvetica Neue", sans-serif;

  --color-brand-blue: #1456f0;
  --color-brand-blue-hover: #2563eb;
  --color-brand-blue-light: #3b82f6;
  --color-brand-pink: #ea5ec1;
  --color-text-primary: #222222;
  --color-text-secondary: #45515e;
  --color-text-muted: #8e8e93;
  --color-surface-dark: #181e25;
  --color-surface-footer: #181e25;
  --color-border: #e5e7eb;
  --color-border-subtle: #f2f3f5;
  --color-bg-glass: hsla(0, 0%, 100%, 0.4);

  --shadow-card: rgba(0, 0, 0, 0.08) 0px 4px 6px;
  --shadow-ambient: rgba(0, 0, 0, 0.08) 0px 0px 22.576px;
  --shadow-brand: rgba(44, 30, 116, 0.16) 0px 0px 15px;
  --shadow-elevated: rgba(36, 36, 36, 0.08) 0px 12px 16px -4px;

  --radius-btn: 8px;
  --radius-card-sm: 13px;
  --radius-card-md: 20px;
  --radius-card-lg: 24px;
  --radius-pill: 9999px;

  --spacing-section: 80px;
  --spacing-section-mobile: 40px;
}
```

## CSP rules (enforced by nginx)
No unsafe-inline, no unsafe-eval.
Vite production build does NOT inline scripts — no workarounds needed.
If Tailwind adds inline styles → use sha256 hash of that exact block, not broad unsafe-inline.

## index.html requirements
Must include:
1. <link rel="preconnect" href="https://fonts.googleapis.com">
2. <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
3. <link rel="preload" as="image" href="/assets/hero.avif" fetchpriority="high">
4. JSON-LD script tags (WebSite, Organization, Service, FAQPage, BreadcrumbList)
5. og:image pointing to /assets/og-cover.png (1200×630px)

## Static-only rule
Landing has ZERO runtime dependency on FastAPI.
All tariffs/prices come from src/lib/constants.ts.
Never add fetch() calls to /api/* endpoints.

## Quality gates before commit
npx eslint . --fix
npx tsc --noEmit
npm run build   # includes prebuild → sitemap.xml
npx lhci autorun
