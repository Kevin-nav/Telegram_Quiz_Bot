import logging
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
    state.dispatcher = TelegramUpdateDispatcher(state)
    state.telegram_app.bot_data["background_scheduler"] = state.dispatcher
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
    logger.info("Starting up Adarkwa Study Bot web application.")

    if state.arq_pool is None:
        state.arq_pool = await init_arq_pool()

    await state.telegram_app.initialize()
    await state.telegram_app.start()
    await set_bot_commands(state.telegram_app)

    if state.settings.webhook_url:
        webhook_path = f"{state.settings.webhook_url.rstrip('/')}/webhook"
        await state.telegram_app.bot.set_webhook(
            url=webhook_path,
            secret_token=state.settings.webhook_secret,
            allowed_updates=["message", "callback_query", "poll_answer"],
            max_connections=100,
        )


async def shutdown_web_app(state: ApplicationState) -> None:
    logger.info("Shutting down Adarkwa Study Bot web application.")

    if state.dispatcher is not None:
        await state.dispatcher.shutdown()

    await state.telegram_app.stop()
    await state.telegram_app.shutdown()
    await close_arq_pool()


async def startup_worker_app(state: ApplicationState) -> None:
    logger.info("Starting up Adarkwa Study Bot worker.")
    await state.telegram_app.initialize()


async def shutdown_worker_app(state: ApplicationState) -> None:
    logger.info("Shutting down Adarkwa Study Bot worker.")
    await state.telegram_app.shutdown()
