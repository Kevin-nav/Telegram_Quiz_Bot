import pytest

from src.core.config import Settings
from src.core.security import DEFAULT_WEBHOOK_SECRET


def test_production_requires_non_default_webhook_secret(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123456:real-token")
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql+asyncpg://user:pass@host/db?sslmode=require"
    )
    monkeypatch.setenv("WEBHOOK_SECRET", DEFAULT_WEBHOOK_SECRET)

    with pytest.raises(ValueError, match="WEBHOOK_SECRET"):
        Settings()


def test_production_requires_https_webhook_url(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123456:real-token")
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql+asyncpg://user:pass@host/db?sslmode=require"
    )
    monkeypatch.setenv("WEBHOOK_SECRET", "this-is-a-strong-secret")
    monkeypatch.setenv("WEBHOOK_URL", "http://example.com/webhook")

    with pytest.raises(ValueError, match="WEBHOOK_URL"):
        Settings()


def test_testing_environment_allows_non_https_webhook(monkeypatch):
    monkeypatch.setenv("APP_ENV", "testing")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/test_db"
    )
    monkeypatch.setenv("WEBHOOK_SECRET", "test-secret")
    monkeypatch.setenv("WEBHOOK_URL", "http://example.com/webhook")

    settings = Settings()

    assert settings.app_env == "testing"
    assert settings.webhook_url == "http://example.com/webhook"


def test_sync_database_url_is_accepted_and_normalized(monkeypatch):
    monkeypatch.setenv("APP_ENV", "testing")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost/test_db")

    settings = Settings()

    assert settings.async_database_url.startswith("postgresql+asyncpg://")
    assert settings.sync_database_url.startswith("postgresql://")


def test_async_database_url_strips_asyncpg_incompatible_query_params(monkeypatch):
    monkeypatch.setenv("APP_ENV", "testing")
    monkeypatch.setenv(
        "DATABASE_URL",
        (
            "postgresql://user:pass@host/db"
            "?sslmode=require&channel_binding=require&application_name=study-bot"
        ),
    )

    settings = Settings()

    assert settings.async_database_url == (
        "postgresql+asyncpg://user:pass@host/db?application_name=study-bot"
    )
    assert settings.async_database_connect_args == {"ssl": "require"}


def test_arq_queue_name_defaults_to_background_v2(monkeypatch):
    monkeypatch.setenv("APP_ENV", "testing")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost/test_db")

    settings = Settings()

    assert settings.arq_queue_name == "adarkwa-bot-background-v2"
