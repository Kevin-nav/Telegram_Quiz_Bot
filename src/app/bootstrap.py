import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any

from src.app.logging import configure_logging
from src.app.observability import initialize_observability
from src.api.telegram_dispatcher import TelegramUpdateDispatcher
from src.bot.application import get_telegram_applications, set_bot_commands
from src.bot.runtime_config import BOT_CONFIG_KEY, TANJAH_BOT_ID
from src.cache import redis_client
from src.core.config import Settings, get_settings
from src.database import AsyncSessionLocal, engine
from src.domains.catalog.learner_service import LearnerCatalogService
from src.domains.catalog.service import CatalogService
from src.domains.home.service import HomeService
from src.domains.performance.service import PerformanceService
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
    telegram_apps: dict[str, Any]
    state_stores: dict[str, InteractiveStateStore]
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
        telegram_app=None,
        telegram_apps={},
        state_stores={},
        redis=redis_client,
        db_engine=engine,
        db_session_factory=AsyncSessionLocal,
        state_store=InteractiveStateStore(redis_client),
    )
    state.telegram_apps = get_telegram_applications(settings.bot_configs)
    state.state_stores = {
        bot_id: InteractiveStateStore(redis_client, bot_id=bot_id)
        for bot_id in state.telegram_apps
    }
    state.telegram_app = state.telegram_apps[TANJAH_BOT_ID]
    state.state_store = state.state_stores[TANJAH_BOT_ID]
    if include_arq:
        state.arq_pool = await init_arq_pool()
    configure_application_services(state)
    return state


def configure_application_services(state: ApplicationState) -> None:
    for bot_id, telegram_app in _get_telegram_apps(state).items():
        state_store = _get_state_store_for_bot(state, bot_id)
        bot_config = telegram_app.bot_data.get(BOT_CONFIG_KEY)
        telegram_app.bot_data["catalog_service"] = LearnerCatalogService(
            catalog_service=CatalogService(
                state_store=state_store,
                allowed_course_codes=getattr(bot_config, "allowed_course_codes", ()),
                fixed_faculty_code=getattr(bot_config, "fixed_faculty_code", None),
                fixed_level_code=getattr(bot_config, "fixed_level_code", None),
            )
        )
        telegram_app.bot_data["home_service"] = HomeService(
            button_labels=getattr(getattr(bot_config, "theme", None), "button_labels", None)
        )
        telegram_app.bot_data["profile_service"] = ProfileService(
            session_factory=state.db_session_factory,
            state_store=state_store,
            bot_id=bot_id,
        )
        telegram_app.bot_data["performance_service"] = PerformanceService(bot_id=bot_id)
        telegram_app.bot_data["quiz_session_service"] = QuizSessionService(
            state_store=state_store,
            bot_id=bot_id,
        )
        telegram_app.bot_data["state_store"] = state_store


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

        try:
            for telegram_app in _get_telegram_apps(state).values():
                await telegram_app.initialize()
            state.telegram_initialized = True
            for telegram_app in _get_telegram_apps(state).values():
                await telegram_app.start()
            state.telegram_started = True
            for telegram_app in _get_telegram_apps(state).values():
                await set_bot_commands(telegram_app)
            state.dispatcher = TelegramUpdateDispatcher(state)
            for telegram_app in _get_telegram_apps(state).values():
                telegram_app.bot_data["background_scheduler"] = state.dispatcher

            if state.settings.webhook_url:
                webhook_base_url = state.settings.webhook_url.rstrip("/")
                for bot_id, telegram_app in _get_telegram_apps(state).items():
                    bot_config = _get_webhook_bot_config(state, bot_id)
                    await telegram_app.bot.set_webhook(
                        url=f"{webhook_base_url}{bot_config.webhook_path}",
                        secret_token=bot_config.webhook_secret,
                        allowed_updates=[
                            "message",
                            "callback_query",
                            "poll_answer",
                        ],
                        max_connections=100,
                    )
                state.webhook_registered = True

            state.startup_ready = True
            state.startup_error = None
        except Exception as exc:
            state.startup_error = f"telegram_startup_failed:{exc.__class__.__name__}"
            logger.exception("Telegram startup failed; cleaning up partial startup state.")

            if state.webhook_registered:
                for telegram_app in _get_telegram_apps(state).values():
                    try:
                        await telegram_app.bot.delete_webhook()
                    except Exception:
                        logger.exception(
                            "Failed to remove webhook during startup cleanup."
                        )
                state.webhook_registered = False

            if state.dispatcher is not None:
                try:
                    await state.dispatcher.shutdown()
                finally:
                    state.dispatcher = None
                    for telegram_app in _get_telegram_apps(state).values():
                        telegram_app.bot_data.pop("background_scheduler", None)

            if state.telegram_started:
                try:
                    for telegram_app in _get_telegram_apps(state).values():
                        await telegram_app.stop()
                finally:
                    state.telegram_started = False

            if state.telegram_initialized:
                try:
                    for telegram_app in _get_telegram_apps(state).values():
                        await telegram_app.shutdown()
                finally:
                    state.telegram_initialized = False

            state.startup_ready = False
            return


async def shutdown_web_app(state: ApplicationState) -> None:
    logger.info("Shutting down Adarkwa Study Bot web application.")

    if state.dispatcher is not None:
        await state.dispatcher.shutdown()

    if state.telegram_started:
        for telegram_app in _get_telegram_apps(state).values():
            await telegram_app.stop()
        state.telegram_started = False
    if state.telegram_initialized:
        for telegram_app in _get_telegram_apps(state).values():
            await telegram_app.shutdown()
        state.telegram_initialized = False
    state.telegram_started = False
    state.webhook_registered = False
    state.startup_ready = False
    state.dispatcher = None
    await close_arq_pool()
    state.arq_pool = None
    state.last_startup_attempt_at = None


async def startup_worker_app(state: ApplicationState) -> None:
    logger.info("Starting up Adarkwa Study Bot worker.")
    for telegram_app in _get_telegram_apps(state).values():
        await telegram_app.initialize()


async def shutdown_worker_app(state: ApplicationState) -> None:
    logger.info("Shutting down Adarkwa Study Bot worker.")
    for telegram_app in _get_telegram_apps(state).values():
        await telegram_app.shutdown()


def _get_telegram_apps(state) -> dict[str, Any]:
    telegram_apps = getattr(state, "telegram_apps", None)
    if isinstance(telegram_apps, dict) and telegram_apps:
        return telegram_apps
    return {TANJAH_BOT_ID: state.telegram_app}


def _get_webhook_bot_config(state, bot_id: str):
    bot_configs = getattr(getattr(state, "settings", None), "bot_configs", None)
    if isinstance(bot_configs, dict) and bot_configs.get(bot_id):
        return bot_configs[bot_id]

    return type(
        "LegacyBotConfig",
        (),
        {
            "webhook_path": "/webhook",
            "webhook_secret": getattr(state.settings, "webhook_secret", None),
        },
    )()


def _get_state_store_for_bot(state, bot_id: str):
    state_stores = getattr(state, "state_stores", None)
    if isinstance(state_stores, dict) and state_stores.get(bot_id):
        return state_stores[bot_id]
    return state.state_store
