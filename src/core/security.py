from urllib.parse import urlparse


DEFAULT_WEBHOOK_SECRET = "super-secret-default-token"
UNSAFE_TOKEN_MARKERS = ("your_", "replace-me", "changeme")


def is_non_local_environment(app_env: str) -> bool:
    return app_env.lower() not in {"local", "development", "dev", "test", "testing"}


def is_secure_webhook_url(url: str | None) -> bool:
    if not url:
        return False

    parsed = urlparse(url)
    return parsed.scheme == "https" and bool(parsed.netloc)


def has_unsafe_secret(secret: str | None) -> bool:
    if not secret:
        return True

    normalized = secret.strip().lower()
    return normalized == DEFAULT_WEBHOOK_SECRET or len(secret.strip()) < 16


def has_placeholder_token(token: str | None) -> bool:
    if not token:
        return True

    normalized = token.strip().lower()
    return any(marker in normalized for marker in UNSAFE_TOKEN_MARKERS)


def normalize_async_database_url(database_url: str) -> str:
    if database_url.startswith("postgresql+asyncpg://"):
        return database_url
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    raise ValueError("DATABASE_URL must start with postgresql:// or postgresql+asyncpg://.")


def normalize_sync_database_url(database_url: str) -> str:
    if database_url.startswith("postgresql://"):
        return database_url
    if database_url.startswith("postgresql+asyncpg://"):
        return database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    raise ValueError("DATABASE_URL must start with postgresql:// or postgresql+asyncpg://.")
