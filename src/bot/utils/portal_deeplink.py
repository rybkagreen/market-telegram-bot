"""Portal deeplink helpers.

Bot cannot accept PII (per project rule + ФЗ-152). Setup flows that need
bank requisites or legal-profile data live exclusively in the web portal.

The bridge is two-hop:
  1. Bot inline button uses WebAppInfo pointing at the mini_app at the
     target path.
  2. The mini_app screen is a placeholder that wraps `OpenInWebPortal`
     (Phase 1) — it exchanges the mini_app JWT for a one-shot ticket via
     POST /api/auth/exchange-miniapp-to-portal and opens the portal at
     `/login/ticket?ticket=...&redirect=<target>`.

The bot itself never possesses a mini_app JWT and so cannot call the
exchange endpoint directly; the indirection is intentional and reuses
the existing Phase 1 infrastructure.
"""

from aiogram.types import WebAppInfo

from src.config.settings import settings


def portal_webapp(target: str) -> WebAppInfo:
    """Return WebAppInfo opening the mini_app at the given internal path.

    Path must start with `/`. The mini_app at that path is expected to
    redirect to the web portal via OpenInWebPortal.
    """
    base = settings.mini_app_url.rstrip("/")
    return WebAppInfo(url=f"{base}{target}")
