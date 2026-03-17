from telegram import Update
from telegram.ext import ContextTypes

from src.analytics.internal_analytics import analytics
from src.bot.copy import build_home_message, build_welcome_message
from src.bot.keyboards import build_home_keyboard, build_welcome_keyboard
from src.domains.home.service import HomeService
from src.domains.profile.service import ProfileService


def _humanize(code: str | None, fallback: str | None = None) -> str | None:
    if code:
        return code.replace("-", " ").title()
    return fallback


def _get_profile_service(context: ContextTypes.DEFAULT_TYPE) -> ProfileService:
    return context.application.bot_data.get("profile_service", ProfileService())


def _get_home_service(context: ContextTypes.DEFAULT_TYPE) -> HomeService:
    return context.application.bot_data.get("home_service", HomeService())


def _build_home_profile(user) -> dict[str, str | None]:
    return {
        "faculty_name": _humanize(getattr(user, "faculty_code", None), "Not set"),
        "program_name": _humanize(getattr(user, "program_code", None), "Not set"),
        "level_name": f"Level {getattr(user, 'level_code', None)}"
        if getattr(user, "level_code", None)
        else "Not set",
        "semester_name": _humanize(getattr(user, "semester_code", None), "Not set"),
        "course_name": _humanize(
            getattr(user, "preferred_course_code", None), "No course selected"
        ),
    }


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    telegram_user = update.effective_user

    await analytics.track_event(
        user_id=telegram_user.id,
        event_type="User Registered",
        metadata={
            "username": telegram_user.username,
            "first_name": telegram_user.first_name,
        },
    )

    profile_service = _get_profile_service(context)
    home_service = _get_home_service(context)
    user = await profile_service.load_or_initialize_user(
        telegram_user.id,
        display_name=telegram_user.first_name or telegram_user.full_name,
    )

    if not getattr(user, "onboarding_completed", False):
        await update.message.reply_text(
            build_welcome_message(telegram_user.first_name or telegram_user.full_name),
            reply_markup=build_welcome_keyboard(),
        )
        return

    home = home_service.build_home(
        _build_home_profile(user),
        has_active_quiz=getattr(user, "has_active_quiz", False),
    )
    await update.message.reply_text(
        build_home_message(_build_home_profile(user)),
        reply_markup=build_home_keyboard(home["buttons"]),
    )
