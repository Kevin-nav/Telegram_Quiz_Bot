import logging

from telegram import Update
from telegram.ext import ContextTypes

from src.bot.copy import (
    build_help_message,
    build_performance_placeholder,
)
from src.bot.keyboards import build_home_keyboard, build_quiz_length_keyboard
from src.domains.home.service import HomeService
from src.domains.profile.service import ProfileService
from src.domains.quiz_entry.service import QuizEntryService

logger = logging.getLogger(__name__)


def _humanize(code: str | None, fallback: str) -> str:
    if not code:
        return fallback
    return code.replace("-", " ").title()


def _build_home_profile(user) -> dict[str, str]:
    return {
        "faculty_name": _humanize(getattr(user, "faculty_code", None), "Not set"),
        "program_name": _humanize(getattr(user, "program_code", None), "Not set"),
        "level_name": (
            f"Level {user.level_code}"
            if getattr(user, "level_code", None)
            else "Not set"
        ),
    }


def _get_profile_service(context: ContextTypes.DEFAULT_TYPE) -> ProfileService:
    return context.application.bot_data.get("profile_service", ProfileService())


def _get_home_service(context: ContextTypes.DEFAULT_TYPE) -> HomeService:
    return context.application.bot_data.get("home_service", HomeService())


def _get_quiz_entry_service(context: ContextTypes.DEFAULT_TYPE) -> QuizEntryService:
    return context.application.bot_data.get("quiz_entry_service", QuizEntryService())


def _course_name(user) -> str:
    course = getattr(user, "preferred_course_code", None)
    if not course:
        return "Your Course"
    return course.replace("-", " ").title()


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    profile_service = _get_profile_service(context)
    user = await profile_service.load_or_initialize_user(update.effective_user.id)

    home_service = _get_home_service(context)
    home = home_service.build_home(
        _build_home_profile(user),
        has_active_quiz=getattr(user, "has_active_quiz", False),
    )

    await update.message.reply_text(
        text=build_help_message(),
        reply_markup=build_home_keyboard(home["buttons"]),
    )


async def performance_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    profile_service = _get_profile_service(context)
    user = await profile_service.load_or_initialize_user(update.effective_user.id)

    home_service = _get_home_service(context)
    home = home_service.build_home(
        _build_home_profile(user),
        has_active_quiz=getattr(user, "has_active_quiz", False),
    )

    await update.message.reply_text(
        text=build_performance_placeholder(),
        reply_markup=build_home_keyboard(home["buttons"]),
    )


async def quiz_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    quiz_entry_service = _get_quiz_entry_service(context)
    profile_service = _get_profile_service(context)
    user = await profile_service.load_or_initialize_user(update.effective_user.id)

    await update.message.reply_text(
        text=quiz_entry_service.build_length_prompt(_course_name(user)),
        reply_markup=build_quiz_length_keyboard(quiz_entry_service.QUESTION_COUNTS),
    )
