# CHANGES — 2026-04-12 — ChannelCard UI Refactor (Mini App)

**Session date:** 2026-04-12
**Verified against:** `feature/S-27-web-portal` branch
**Status:** Production ready

---

## Summary

| # | Change | Type | Files |
|---|--------|------|-------|
| 1 | ChannelCard 3-zone layout refactor | UX | `mini_app/src/components/ui/ChannelCard.tsx`, `ChannelCard.module.css` |

---

## 1. ChannelCard UI Refactor

**Problem:** Flat visual hierarchy — all text elements had similar weight (name 13px, stats 11px). No clear separation between header, body, footer. StatusPill pushed to the right edge, competing with content. No touch feedback indicator.

**Fix:** Complete redesign with 3-zone layout:

### Before
```
[Avatar]  Name · @username         StatusPill
          Category · 👥 subs        >
```

### After
```
┌─────────────────────────────────────┐
│ [Avatar] Channel Name         [✓]   │  ← Header: large title + status
│          @username                  │
│ ─────────────────────────────────── │
│ 12 345       💼 Бизнес     5 000 ₽  │  ← Body: stats grid
│ подписчиков  категория    за пост    │
│ ─────────────────────────────────── │
│                                  ›  │  ← Footer: chevron action hint
└─────────────────────────────────────┘
```

### Design Decisions
- **No inline-styles** — all styling via CSS modules using existing design tokens (`--rh-*`)
- **Typography hierarchy**: Name `var(--rh-text-base)` 15px semibold (display font) → Stats `var(--rh-text-sm)` 13px semibold → Labels `var(--rh-text-2xs)` 10px muted
- **Header**: Avatar (44×44px) + Title block + StatusPill in flex row
- **Body**: Stats in flex-wrap row with `border-top` separator, each stat as value/label pair
- **Footer**: Chevron right for clickable cards, transitions to accent color on hover/active
- **Touch targets**: Avatar 44×44px (iOS standard), entire card clickable with `scale(0.985)` press feedback
- **Overflow protection**: `truncate` + `min-width: 0` on all text containers

### Design Tokens Used
| Token | Value | Usage |
|-------|-------|-------|
| `--rh-text-base` | 15px | Channel name |
| `--rh-text-sm` | 13px | Stat values |
| `--rh-text-xs` | 11px | Username |
| `--rh-text-2xs` | 10px | Stat labels |
| `--rh-font-display` | 'Outfit' | Name + stat values |
| `--rh-weight-semibold` | 600 | Name + stat values |
| `--rh-space-4` | 16px | Card padding |
| `--rh-radius-lg` | 16px | Card border radius |

---

## Files Modified

| File | Change |
|------|--------|
| `mini_app/src/components/ui/ChannelCard.tsx` | 3-zone layout (header/body/footer), no inline styles |
| `mini_app/src/components/ui/ChannelCard.module.css` | Complete rewrite — flex-col card, flex header, stats grid |

---

🔍 Verified against: `feature/S-27-web-portal` | 📅 Updated: 2026-04-12T16:00:00Z
