from src.core.config import get_settings

_settings = get_settings()

APP_ENV = _settings.app_env
BOT_CONFIGS = _settings.bot_configs
DEFAULT_BOT_CONFIG = _settings.default_bot_config
TELEGRAM_BOT_TOKEN = DEFAULT_BOT_CONFIG.telegram_bot_token
DATABASE_URL = _settings.async_database_url
DATABASE_CONNECT_ARGS = _settings.async_database_connect_args
REDIS_URL = _settings.redis_url
ARQ_QUEUE_NAME = _settings.arq_queue_name
WEBHOOK_URL = _settings.webhook_url
WEBHOOK_SECRET = DEFAULT_BOT_CONFIG.webhook_secret
SENTRY_DSN = _settings.sentry_dsn
WELCOME_MESSAGE = _settings.welcome_message
