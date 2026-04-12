from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.bot.runtime_config import (
    ADARKWA_BOT_ID,
    DEFAULT_BOT_THEMES,
    DEFAULT_PROFILE_SETUP_OVERRIDES,
    TANJAH_BOT_ID,
    BotRuntimeConfig,
    normalize_webhook_path,
    parse_allowed_course_codes,
)
from src.core.security import (
    DEFAULT_WEBHOOK_SECRET,
    build_async_database_config,
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
    app_mode: str = Field(default="normal", alias="APP_MODE")
    telegram_bot_token: str | None = Field(default=None, alias="TELEGRAM_BOT_TOKEN")
    tanjah_bot_token: str | None = Field(default=None, alias="TANJAH_BOT_TOKEN")
    adarkwa_bot_token: str | None = Field(default=None, alias="ADARKWA_BOT_TOKEN")
    database_url: str = Field(alias="DATABASE_URL")
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    arq_queue_name: str = Field(
        default="adarkwa-bot-background-v2",
        alias="ARQ_QUEUE_NAME",
    )
    webhook_url: str | None = Field(default=None, alias="WEBHOOK_URL")
    webhook_secret: str | None = Field(default=None, alias="WEBHOOK_SECRET")
    tanjah_webhook_secret: str | None = Field(
        default=None,
        alias="TANJAH_WEBHOOK_SECRET",
    )
    tanjah_webhook_path: str = Field(
        default="/webhook/tanjah",
        alias="TANJAH_WEBHOOK_PATH",
    )
    tanjah_allowed_course_codes: str = Field(
        default="",
        alias="TANJAH_ALLOWED_COURSE_CODES",
    )
    adarkwa_webhook_secret: str | None = Field(
        default=None,
        alias="ADARKWA_WEBHOOK_SECRET",
    )
    adarkwa_webhook_path: str = Field(
        default="/webhook/adarkwa",
        alias="ADARKWA_WEBHOOK_PATH",
    )
    adarkwa_allowed_course_codes: str = Field(
        default="",
        alias="ADARKWA_ALLOWED_COURSE_CODES",
    )
    sentry_dsn: str | None = Field(default=None, alias="SENTRY_DSN")
    admin_allowed_origins: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000",
        alias="ADMIN_ALLOWED_ORIGINS",
    )
    admin_session_cookie_domain: str | None = Field(
        default=None,
        alias="ADMIN_SESSION_COOKIE_DOMAIN",
    )
    r2_account_id: str | None = Field(default=None, alias="R2_ACCOUNT_ID")
    r2_access_key_id: str | None = Field(default=None, alias="R2_ACCESS_KEY_ID")
    r2_secret_access_key: str | None = Field(
        default=None, alias="R2_SECRET_ACCESS_KEY"
    )
    r2_bucket_name: str | None = Field(default=None, alias="R2_BUCKET_NAME")
    r2_public_base_url: str | None = Field(default=None, alias="R2_PUBLIC_BASE_URL")
    r2_db_backup_prefix: str = Field(
        default="db-backups",
        alias="R2_DB_BACKUP_PREFIX",
    )
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
        if self.admin_session_cookie_domain == "":
            self.admin_session_cookie_domain = None

        self.app_mode = self.app_mode.strip().lower()
        if self.app_mode not in {"normal", "queue_only"}:
            raise ValueError("APP_MODE must be one of: normal, queue_only.")

        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable not set.")
        normalize_async_database_url(self.database_url)

        if is_non_local_environment(self.app_env):
            for bot_id, bot_config in self.bot_configs.items():
                if not bot_config.telegram_bot_token:
                    raise ValueError(
                        f"{bot_id.upper()}_BOT_TOKEN environment variable not set."
                    )
                if has_placeholder_token(bot_config.telegram_bot_token):
                    raise ValueError(
                        f"{bot_id.upper()}_BOT_TOKEN appears to be a placeholder value."
                    )
                if has_unsafe_secret(bot_config.webhook_secret):
                    raise ValueError(
                        f"{bot_id.upper()}_WEBHOOK_SECRET must be set to a strong non-default value."
                    )
            if self.webhook_url and not is_secure_webhook_url(self.webhook_url):
                raise ValueError(
                    "WEBHOOK_URL must use https in non-local environments."
                )

        return self

    @property
    def async_database_url(self) -> str:
        async_database_url, _ = build_async_database_config(self.database_url)
        return async_database_url

    @property
    def async_database_connect_args(self) -> dict[str, object]:
        _, connect_args = build_async_database_config(self.database_url)
        return connect_args

    @property
    def sync_database_url(self) -> str:
        return normalize_sync_database_url(self.database_url)

    @property
    def parsed_admin_allowed_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.admin_allowed_origins.split(",")
            if origin.strip()
        ]

    @property
    def bot_configs(self) -> dict[str, BotRuntimeConfig]:
        configs = {
            TANJAH_BOT_ID: BotRuntimeConfig(
                bot_id=TANJAH_BOT_ID,
                telegram_bot_token=self.tanjah_bot_token or self.telegram_bot_token,
                webhook_secret=self.tanjah_webhook_secret or self.webhook_secret,
                webhook_path=normalize_webhook_path(
                    self.tanjah_webhook_path,
                    fallback_bot_id=TANJAH_BOT_ID,
                ),
                allowed_course_codes=parse_allowed_course_codes(
                    self.tanjah_allowed_course_codes
                ),
                theme=DEFAULT_BOT_THEMES[TANJAH_BOT_ID],
                **DEFAULT_PROFILE_SETUP_OVERRIDES[TANJAH_BOT_ID],
            ),
        }

        if self._adarkwa_configured:
            configs[ADARKWA_BOT_ID] = BotRuntimeConfig(
                bot_id=ADARKWA_BOT_ID,
                telegram_bot_token=self.adarkwa_bot_token,
                webhook_secret=self.adarkwa_webhook_secret or self.webhook_secret,
                webhook_path=normalize_webhook_path(
                    self.adarkwa_webhook_path,
                    fallback_bot_id=ADARKWA_BOT_ID,
                ),
                allowed_course_codes=parse_allowed_course_codes(
                    self.adarkwa_allowed_course_codes
                ),
                theme=DEFAULT_BOT_THEMES[ADARKWA_BOT_ID],
                **DEFAULT_PROFILE_SETUP_OVERRIDES[ADARKWA_BOT_ID],
            )

        return configs

    @property
    def default_bot_config(self) -> BotRuntimeConfig:
        return self.bot_configs[TANJAH_BOT_ID]

    @property
    def _adarkwa_configured(self) -> bool:
        return any(
            [
                self.adarkwa_bot_token,
                self.adarkwa_webhook_secret,
                self.adarkwa_allowed_course_codes.strip(),
                self.adarkwa_webhook_path
                and self.adarkwa_webhook_path.strip() != "/webhook/adarkwa",
            ]
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


def reset_settings_cache() -> None:
    get_settings.cache_clear()


settings = get_settings()

DEFAULTS = {
    "WEBHOOK_SECRET": DEFAULT_WEBHOOK_SECRET,
}
