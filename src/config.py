from src.core.config import get_settings

_settings = get_settings()

APP_ENV = _settings.app_env
TELEGRAM_BOT_TOKEN = _settings.telegram_bot_token
DATABASE_URL = _settings.async_database_url
REDIS_URL = _settings.redis_url
WEBHOOK_URL = _settings.webhook_url
WEBHOOK_SECRET = _settings.webhook_secret
SENTRY_DSN = _settings.sentry_dsn
WELCOME_MESSAGE = _settings.welcome_message
