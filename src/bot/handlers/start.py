import logging

from telegram import Update
from telegram.ext import ContextTypes

from src.bot.copy import build_home_message, build_welcome_message
from src.bot.handlers.command_utils import (
    build_home_profile,
    invalidate_quiz_callback_targets,
    remember_reply_message,
)
from src.bot.keyboards import build_home_keyboard, build_welcome_keyboard
from src.domains.home.service import HomeService
from src.domains.profile.service import ProfileService
from src.infra.redis.state_store import UserProfileRecord
from src.tasks.arq_client import (
    enqueue_record_analytics_event,
)

logger = logging.getLogger(__name__)
ACTIVE_INTERACTIVE_MESSAGE_ID_KEY = "active_interactive_message_id"


def _humanize(code: str | None, fallback: str | None = None) -> str | None:
    if code:
        return code.replace("-", " ").title()
    return fallback


def _get_profile_service(context: ContextTypes.DEFAULT_TYPE) -> ProfileService:
    return context.application.bot_data.get("profile_service", ProfileService())


def _get_home_service(context: ContextTypes.DEFAULT_TYPE) -> HomeService:
    return context.application.bot_data.get("home_service", HomeService())


def _get_background_scheduler(context: ContextTypes.DEFAULT_TYPE):
    return context.application.bot_data.get("background_scheduler")


def _get_state_store(context: ContextTypes.DEFAULT_TYPE):
    return context.application.bot_data.get("state_store")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    telegram_user = update.effective_user

    profile_service = _get_profile_service(context)
    home_service = _get_home_service(context)
    state_store = _get_state_store(context)
    user = await profile_service.load_or_initialize_user(
        telegram_user.id,
        display_name=telegram_user.first_name or telegram_user.full_name,
    )
    await invalidate_quiz_callback_targets(context, user_id=telegram_user.id)

    if not getattr(user, "onboarding_completed", False):
        reply = await update.message.reply_text(
            build_welcome_message(telegram_user.first_name or telegram_user.full_name),
            reply_markup=build_welcome_keyboard(),
        )
    else:
        home = home_service.build_home(
            build_home_profile(user),
            has_active_quiz=getattr(user, "has_active_quiz", False),
        )
        reply = await update.message.reply_text(
            build_home_message(build_home_profile(user)),
            reply_markup=build_home_keyboard(home["buttons"]),
        )
    remember_reply_message(context, reply)

    scheduler = _get_background_scheduler(context)
    if scheduler is None:
        return

    if state_store is not None:
        should_track = await state_store.claim_analytics_event(
            telegram_user.id,
            "User Registered",
        )
    else:
        should_track = True
    if should_track:
        scheduler.schedule_coroutine(
            enqueue_record_analytics_event(
                {
                    "user_id": telegram_user.id,
                    "event_type": "User Registered",
                    "metadata": {
                        "username": telegram_user.username,
                        "first_name": telegram_user.first_name,
                    },
                }
            )
        )
