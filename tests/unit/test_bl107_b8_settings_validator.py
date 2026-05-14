"""BL-107 Phase B.8 / BL-002 — Settings.telegram_api_base_url production guard tests.

Validates layer 1 of the R4 guard: model_validator rejects the combination of
sentry_environment == "production" and telegram_api_base_url != None.

Settings fields are aliased (Field(..., alias="UPPERCASE_NAME")) and the
project does NOT enable populate_by_name, so kwargs in tests use the alias
form to match how env vars are interpreted at runtime.
"""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from src.config.settings import Settings

# Required Settings fields filled with obviously-fake low-entropy placeholders.
# Settings does not validate the shape of these keys (no Fernet/HMAC check at
# construction time), so any non-empty string passes. Low entropy keeps gitleaks
# pre-commit hook quiet — real test values live in .env.test.example (allowlisted).
_FAKE_KEY = "fake-test-placeholder-not-a-secret"
_REQUIRED_ENV: dict[str, str] = {
    "BOT_TOKEN": "test_token",
    "API_ID": "1",
    "API_HASH": "test_hash",
    "DATABASE_URL": "postgresql+asyncpg://u:p@localhost/test",
    "REDIS_URL": "redis://localhost:6379/0",
    "CELERY_BROKER_URL": "redis://localhost:6379/0",
    "CELERY_RESULT_BACKEND": "redis://localhost:6379/1",
    "FIELD_ENCRYPTION_KEY": _FAKE_KEY,
    "SEARCH_HASH_KEY": _FAKE_KEY,
    "JWT_SECRET": "test_jwt",
    "BOT_API_HMAC_SECRET": "test_hmac",
}


def _settings_from_env(monkeypatch: pytest.MonkeyPatch, **overrides: Any) -> Settings:
    """Wire env vars via monkeypatch and instantiate Settings without .env file.

    Bypassing .env keeps each test isolated from the project's real
    configuration; overrides win over the baseline so tests can set or unset
    the two fields under test (SENTRY_ENVIRONMENT, TELEGRAM_API_BASE_URL).
    """
    base = dict(_REQUIRED_ENV)
    for key in ("SENTRY_ENVIRONMENT", "TELEGRAM_API_BASE_URL"):
        monkeypatch.delenv(key, raising=False)
    for key, value in {**base, **overrides}.items():
        if value is None:
            monkeypatch.delenv(key, raising=False)
        else:
            monkeypatch.setenv(key, str(value))
    return Settings(_env_file=None)  # type: ignore[call-arg]


def test_production_with_base_url_raises(monkeypatch: pytest.MonkeyPatch):
    with pytest.raises(ValidationError) as exc_info:
        _settings_from_env(
            monkeypatch,
            SENTRY_ENVIRONMENT="production",
            TELEGRAM_API_BASE_URL="http://stub:8081",
        )
    assert "TELEGRAM_API_BASE_URL must be None" in str(exc_info.value)


def test_production_without_base_url_accepted(monkeypatch: pytest.MonkeyPatch):
    settings = _settings_from_env(
        monkeypatch,
        SENTRY_ENVIRONMENT="production",
        TELEGRAM_API_BASE_URL=None,
    )
    assert settings.telegram_api_base_url is None
    assert settings.sentry_environment == "production"


def test_test_environment_with_base_url_accepted(monkeypatch: pytest.MonkeyPatch):
    settings = _settings_from_env(
        monkeypatch,
        SENTRY_ENVIRONMENT="test",
        TELEGRAM_API_BASE_URL="http://telegram-stub:8081",
    )
    assert settings.telegram_api_base_url == "http://telegram-stub:8081"
    assert settings.sentry_environment == "test"


def test_development_environment_with_base_url_accepted(monkeypatch: pytest.MonkeyPatch):
    settings = _settings_from_env(
        monkeypatch,
        SENTRY_ENVIRONMENT="development",
        TELEGRAM_API_BASE_URL="http://localhost:8081",
    )
    assert settings.telegram_api_base_url == "http://localhost:8081"


def test_default_environment_is_production_safe(monkeypatch: pytest.MonkeyPatch):
    """Omitting both fields keeps prod-safe behavior — base_url defaults to None
    and sentry_environment defaults to 'production'."""
    settings = _settings_from_env(monkeypatch)
    assert settings.sentry_environment == "production"
    assert settings.telegram_api_base_url is None
