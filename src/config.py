from src.core.config import get_settings

_settings = get_settings()

APP_ENV = _settings.app_env
TELEGRAM_BOT_TOKEN = _settings.telegram_bot_token
DATABASE_URL = _settings.async_database_url
DATABASE_CONNECT_ARGS = _settings.async_database_connect_args
REDIS_URL = _settings.redis_url
ARQ_QUEUE_NAME = _settings.arq_queue_name
ADAPTIVE_SELECTOR_ENABLED = _settings.adaptive_selector_enabled
ADAPTIVE_UPDATER_ENABLED = _settings.adaptive_updater_enabled
ADAPTIVE_REVIEW_JOBS_ENABLED = _settings.adaptive_review_jobs_enabled
ADAPTIVE_SNAPSHOT_CACHE_ENABLED = _settings.adaptive_snapshot_cache_enabled
ADAPTIVE_ROLLOUT_COHORT = _settings.adaptive_rollout_cohort
WEBHOOK_URL = _settings.webhook_url
WEBHOOK_SECRET = _settings.webhook_secret
SENTRY_DSN = _settings.sentry_dsn
WELCOME_MESSAGE = _settings.welcome_message
