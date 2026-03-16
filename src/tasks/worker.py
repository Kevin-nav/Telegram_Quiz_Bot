import logging
from typing import Any

from arq.connections import RedisSettings

from src.app.bootstrap import (
    create_app_state,
    shutdown_worker_app,
    startup_worker_app,
)
from src.app.observability import initialize_observability
from src.config import REDIS_URL, SENTRY_DSN
from src.workers.telegram_update import process_telegram_update as handle_telegram_update


logger = logging.getLogger("arq.worker")


async def startup(ctx: dict[str, Any]) -> None:
    """Runs when the ARQ worker starts."""
    initialize_observability(SENTRY_DSN)
    runtime = await create_app_state()
    ctx["runtime"] = runtime
    await startup_worker_app(runtime)


async def shutdown(ctx: dict[str, Any]) -> None:
    """Runs when the ARQ worker stops."""
    runtime = ctx.get("runtime")
    if runtime is not None:
        await shutdown_worker_app(runtime)


async def process_telegram_update(ctx: dict[str, Any], payload: dict) -> None:
    """Process a Telegram update in the background worker."""
    runtime = ctx["runtime"]

    try:
        await handle_telegram_update(runtime, payload)
    except Exception:
        logger.exception("Failed to process Telegram update.")
        raise


class WorkerSettings:
    functions = [process_telegram_update]
    redis_settings = RedisSettings.from_dsn(REDIS_URL)
    on_startup = startup
    on_shutdown = shutdown
    job_timeout = 60
    max_tries = 3
