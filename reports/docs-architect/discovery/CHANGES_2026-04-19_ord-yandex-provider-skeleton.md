# Changes: ORD Yandex provider skeleton + auto-init from settings
**Date:** 2026-04-19T00:00:00Z
**Author:** Claude Code
**Sprint/Task:** S-38 escrow recovery (follow-up to Pre-Launch Blockers)

## Affected Files
- `src/core/services/ord_yandex_provider.py` — **new** skeleton class `YandexOrdProvider(OrdProvider)`; all methods raise `NotImplementedError` with message "Yandex ORD integration required". Placeholder until real Yandex ORD API v7 contract is signed.
- `src/core/services/ord_service.py` — replaced module-level `_global_provider: OrdProvider = StubOrdProvider()` with `_init_ord_provider_from_settings()` factory. When `ORD_PROVIDER=yandex`, returns `YandexOrdProvider(settings.ord_api_key, settings.ord_api_url)`; raises `RuntimeError` if credentials missing. Otherwise returns `StubOrdProvider()`. Also removed unused `channel_id` / `post_url` params from `report_publication` (commented out in signature — TODO: fully strip in next cleanup).
- `.env.ord.sample` — **new** reference file documenting required env vars for production ORD: `ORD_PROVIDER`, `ORD_API_KEY`, `ORD_API_URL`, `ORD_BLOCK_WITHOUT_ERID`, `ORD_REKHARBOR_ORG_ID`, `ORD_REKHARBOR_INN`.
- `CLAUDE.md` — Pre-Launch Blockers section updated: step 4 now says "Real provider is auto-selected by `ORD_PROVIDER` in settings (no code change needed)" instead of "Replace `StubOrdProvider`". Formatting fix: env-var block split onto multiple lines.

## Business Logic Impact
- Provider selection is now driven purely by env (`ORD_PROVIDER`). Deployments no longer require code edits to switch from stub to real provider.
- `YandexOrdProvider` class exists but raises `NotImplementedError` — it is an **explicit TODO**, not a working integration. Production launch still requires implementing each method (see ФЗ-38 blocker in CLAUDE.md).
- If `ORD_PROVIDER=yandex` without `ORD_API_KEY`/`ORD_API_URL` — app fails fast at startup with `RuntimeError`. Previously this state was silent (stub used everywhere).

## API / FSM / DB Contracts
- No API, FSM, or DB changes.
- Internal: `OrdService.report_publication` signature trimmed — `channel_id` and `post_url` parameters commented out (marked unused). Callers are not yet updated; this is a half-step (tracked as TODO).

## Migration Notes
- Set `ORD_PROVIDER=stub` (or leave unset) on dev/staging to keep current behavior.
- For production: must fill in `ORD_API_KEY`/`ORD_API_URL` before setting `ORD_PROVIDER=yandex`.
- No DB migration required.

🔍 Verified against: `feature/s-38-escrow-recovery` HEAD | 📅 Updated: 2026-04-19
