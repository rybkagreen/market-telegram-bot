"""Web portal route paths used by gate remediation_url fields.

Per ФЗ-152 + plan §3.D, gates surface to web_portal only (mini_app does
not render compliance gate UI). Keep aligned with web_portal/src/App.tsx.

Bot deeplinks (`build_portal_deeplink`) are runtime-minted with short
TTL — unsuitable for API responses that may be cached or stored.
"""

LEGAL_PROFILE = "/legal-profile"
LEGAL_PROFILE_VIEW = "/legal-profile/view"
CONTRACTS = "/contracts"
