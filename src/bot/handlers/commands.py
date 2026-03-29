import logging

from telegram import Update
from telegram.ext import ContextTypes

from src.bot.copy import (
    build_help_message,
    build_performance_message,
)
from src.bot.keyboards import build_home_keyboard
from src.bot.handlers.command_utils import (
    build_home_profile,
    get_home_service,
    get_profile_service,
    invalidate_quiz_callback_targets,
    remember_reply_message,
    reply_with_quiz_entry_message,
)
from src.domains.performance.service import PerformanceService

logger = logging.getLogger(__name__)


def _get_performance_service(
    context: ContextTypes.DEFAULT_TYPE,
) -> PerformanceService:
    return context.application.bot_data.get("performance_service", PerformanceService())


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    profile_service = get_profile_service(context)
    user = await profile_service.load_or_initialize_user(update.effective_user.id)
    await invalidate_quiz_callback_targets(context, user_id=update.effective_user.id)

    home_service = get_home_service(context)
    home = home_service.build_home(
        build_home_profile(user),
        has_active_quiz=getattr(user, "has_active_quiz", False),
    )

    reply = await update.message.reply_text(
        text=build_help_message(),
        reply_markup=build_home_keyboard(home["buttons"]),
    )
    remember_reply_message(context, reply)


async def performance_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    profile_service = get_profile_service(context)
    user = await profile_service.load_or_initialize_user(update.effective_user.id)
    await invalidate_quiz_callback_targets(context, user_id=update.effective_user.id)

    home_service = get_home_service(context)
    home = home_service.build_home(
        build_home_profile(user),
        has_active_quiz=getattr(user, "has_active_quiz", False),
        include_performance_button=False,
    )
    performance_summary = await _get_performance_service(context).get_summary(
        update.effective_user.id
    )

    reply = await update.message.reply_text(
        text=build_performance_message(performance_summary),
        reply_markup=build_home_keyboard(home["buttons"]),
    )
    remember_reply_message(context, reply)


async def quiz_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    profile_service = get_profile_service(context)
    user = await profile_service.load_or_initialize_user(update.effective_user.id)
    await reply_with_quiz_entry_message(update=update, context=context, user=user)
