from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.core.security import (
    DEFAULT_WEBHOOK_SECRET,
    has_placeholder_token,
    has_unsafe_secret,
    is_non_local_environment,
    is_secure_webhook_url,
    normalize_async_database_url,
    normalize_sync_database_url,
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_env: str = Field(default="development", alias="APP_ENV")
    telegram_bot_token: str | None = Field(default=None, alias="TELEGRAM_BOT_TOKEN")
    database_url: str = Field(alias="DATABASE_URL")
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    webhook_url: str | None = Field(default=None, alias="WEBHOOK_URL")
    webhook_secret: str | None = Field(default=None, alias="WEBHOOK_SECRET")
    sentry_dsn: str | None = Field(default=None, alias="SENTRY_DSN")
    r2_account_id: str | None = Field(default=None, alias="R2_ACCOUNT_ID")
    r2_access_key_id: str | None = Field(default=None, alias="R2_ACCESS_KEY_ID")
    r2_secret_access_key: str | None = Field(
        default=None, alias="R2_SECRET_ACCESS_KEY"
    )
    r2_bucket_name: str | None = Field(default=None, alias="R2_BUCKET_NAME")
    r2_public_base_url: str | None = Field(default=None, alias="R2_PUBLIC_BASE_URL")
    welcome_message: str = Field(
        default=(
            "Welcome to Adarkwa Study Bot!\n\n"
            "I'm here to help you master your courses with personalized, adaptive quizzes.\n\n"
            "To get started, simply send /quiz.\n\n"
            "Here are the available commands:\n"
            "/quiz - Start a new adaptive quiz.\n"
            "/performance - See your progress and quiz history.\n"
            "/help - Show this message again.\n\n"
            "Happy studying!"
        ),
        alias="WELCOME_MESSAGE",
    )

    @model_validator(mode="after")
    def validate_runtime_settings(self) -> "Settings":
        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable not set.")
        normalize_async_database_url(self.database_url)

        if is_non_local_environment(self.app_env):
            if not self.telegram_bot_token:
                raise ValueError("TELEGRAM_BOT_TOKEN environment variable not set.")
            if has_placeholder_token(self.telegram_bot_token):
                raise ValueError(
                    "TELEGRAM_BOT_TOKEN appears to be a placeholder value."
                )
            if has_unsafe_secret(self.webhook_secret):
                raise ValueError(
                    "WEBHOOK_SECRET must be set to a strong non-default value."
                )
            if self.webhook_url and not is_secure_webhook_url(self.webhook_url):
                raise ValueError(
                    "WEBHOOK_URL must use https in non-local environments."
                )

        return self

    @property
    def async_database_url(self) -> str:
        return normalize_async_database_url(self.database_url)

    @property
    def sync_database_url(self) -> str:
        return normalize_sync_database_url(self.database_url)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


def reset_settings_cache() -> None:
    get_settings.cache_clear()


settings = get_settings()

DEFAULTS = {
    "WEBHOOK_SECRET": DEFAULT_WEBHOOK_SECRET,
}
