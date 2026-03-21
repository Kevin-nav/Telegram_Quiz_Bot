import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any

from src.app.logging import configure_logging
from src.app.observability import initialize_observability
from src.api.telegram_dispatcher import TelegramUpdateDispatcher
from src.bot import telegram_app
from src.bot.application import set_bot_commands
from src.cache import redis_client
from src.core.config import Settings, get_settings
from src.database import AsyncSessionLocal, engine
from src.domains.profile.service import ProfileService
from src.domains.quiz.service import QuizSessionService
from src.infra.redis.state_store import InteractiveStateStore
from src.tasks.arq_client import close_arq_pool, init_arq_pool

logger = logging.getLogger(__name__)
_startup_lock = asyncio.Lock()


@dataclass
class ApplicationState:
    settings: Settings
    telegram_app: Any
    redis: Any
    db_engine: Any
    db_session_factory: Any
    state_store: InteractiveStateStore
    dispatcher: TelegramUpdateDispatcher | None = None
    arq_pool: Any = None
    startup_ready: bool = False
    startup_error: str | None = None
    telegram_initialized: bool = False
    telegram_started: bool = False
    webhook_registered: bool = False
    last_startup_attempt_at: float | None = None
    startup_retry_interval_seconds: float = 30.0


async def create_app_state(*, include_arq: bool = False) -> ApplicationState:
    configure_logging()

    settings = get_settings()
    initialize_observability(settings.sentry_dsn)

    state = ApplicationState(
        settings=settings,
        telegram_app=telegram_app,
        redis=redis_client,
        db_engine=engine,
        db_session_factory=AsyncSessionLocal,
        state_store=InteractiveStateStore(redis_client),
    )
    if include_arq:
        state.arq_pool = await init_arq_pool()
    configure_application_services(state)
    return state


def configure_application_services(state: ApplicationState) -> None:
    state.telegram_app.bot_data["profile_service"] = ProfileService(
        session_factory=state.db_session_factory,
        state_store=state.state_store,
    )
    state.telegram_app.bot_data["quiz_session_service"] = QuizSessionService(
        state_store=state.state_store
    )
    state.telegram_app.bot_data["state_store"] = state.state_store


async def startup_web_app(state: ApplicationState) -> None:
    async with _startup_lock:
        if getattr(state, "startup_ready", False):
            return
        last_startup_attempt_at = getattr(state, "last_startup_attempt_at", None)
        startup_retry_interval_seconds = getattr(
            state,
            "startup_retry_interval_seconds",
            30.0,
        )
        if (
            last_startup_attempt_at is not None
            and time.monotonic() - last_startup_attempt_at
            < startup_retry_interval_seconds
        ):
            return

        state.last_startup_attempt_at = time.monotonic()
        logger.info("Starting up Adarkwa Study Bot web application.")

        if state.arq_pool is None:
            try:
                state.arq_pool = await init_arq_pool()
            except Exception as exc:
                state.startup_error = f"redis_unavailable:{exc.__class__.__name__}"
                logger.exception(
                    "Starting in degraded mode because Redis/ARQ initialization failed."
                )
                return

        await state.telegram_app.initialize()
        state.telegram_initialized = True
        await state.telegram_app.start()
        state.telegram_started = True
        await set_bot_commands(state.telegram_app)
        state.dispatcher = TelegramUpdateDispatcher(state)
        state.telegram_app.bot_data["background_scheduler"] = state.dispatcher

        if state.settings.webhook_url:
            webhook_path = f"{state.settings.webhook_url.rstrip('/')}/webhook"
            await state.telegram_app.bot.set_webhook(
                url=webhook_path,
                secret_token=state.settings.webhook_secret,
                allowed_updates=["message", "callback_query", "poll_answer"],
                max_connections=100,
            )
            state.webhook_registered = True

        state.startup_ready = True
        state.startup_error = None


async def shutdown_web_app(state: ApplicationState) -> None:
    logger.info("Shutting down Adarkwa Study Bot web application.")

    if state.dispatcher is not None:
        await state.dispatcher.shutdown()

    if state.telegram_started:
        await state.telegram_app.stop()
        state.telegram_started = False
    if state.telegram_initialized:
        await state.telegram_app.shutdown()
        state.telegram_initialized = False
    state.startup_ready = False
    state.dispatcher = None
    await close_arq_pool()


async def startup_worker_app(state: ApplicationState) -> None:
    logger.info("Starting up Adarkwa Study Bot worker.")
    await state.telegram_app.initialize()


async def shutdown_worker_app(state: ApplicationState) -> None:
    logger.info("Shutting down Adarkwa Study Bot worker.")
    await state.telegram_app.shutdown()
