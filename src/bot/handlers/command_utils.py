from __future__ import annotations

import inspect

from telegram.ext import ContextTypes

from src.bot.copy import (
    build_incomplete_study_profile_message,
    build_missing_course_message,
    build_quiz_course_prompt,
)
from src.bot.handlers.home import ACTIVE_INTERACTIVE_MESSAGE_ID_KEY
from src.bot.keyboards import build_home_keyboard, build_quiz_course_keyboard
from src.bot.runtime_config import BOT_CONFIG_KEY, BotThemeConfig
from src.domains.catalog.navigation_service import CatalogNavigationService
from src.domains.home.service import HomeService
from src.domains.profile.service import ProfileService
from src.domains.quiz.service import QuizSessionService


def humanize(code: str | None, fallback: str) -> str:
    if not code:
        return fallback
    return code.replace("-", " ").title()


def build_home_profile(user) -> dict[str, str]:
    return {
        "faculty_name": humanize(getattr(user, "faculty_code", None), "Not set"),
        "program_name": humanize(getattr(user, "program_code", None), "Not set"),
        "level_name": (
            f"Level {user.level_code}"
            if getattr(user, "level_code", None)
            else "Not set"
        ),
        "semester_name": humanize(getattr(user, "semester_code", None), "Not set"),
    }


def get_profile_service(context: ContextTypes.DEFAULT_TYPE) -> ProfileService:
    return context.application.bot_data.get("profile_service", ProfileService())


def get_home_service(context: ContextTypes.DEFAULT_TYPE) -> HomeService:
    return context.application.bot_data.get("home_service", HomeService())


def get_quiz_session_service(
    context: ContextTypes.DEFAULT_TYPE,
) -> QuizSessionService:
    return context.application.bot_data.get("quiz_session_service", QuizSessionService())


def get_catalog_service(
    context: ContextTypes.DEFAULT_TYPE,
) -> CatalogNavigationService:
    return context.application.bot_data.get(
        "catalog_service", CatalogNavigationService()
    )


def get_bot_theme(
    context: ContextTypes.DEFAULT_TYPE,
) -> BotThemeConfig | None:
    bot_config = context.application.bot_data.get(BOT_CONFIG_KEY)
    return getattr(bot_config, "theme", None)


async def maybe_await(value):
    if inspect.isawaitable(value):
        return await value
    return value


async def catalog_call(context: ContextTypes.DEFAULT_TYPE, method_name: str, *args):
    catalog_service = get_catalog_service(context)
    method = getattr(catalog_service, method_name)
    return await maybe_await(method(*args))


def user_has_complete_profile(user) -> bool:
    return all(
        getattr(user, field, None)
        for field in ("faculty_code", "program_code", "level_code", "semester_code")
    )


async def get_profile_courses(context: ContextTypes.DEFAULT_TYPE, user) -> list[dict[str, str]]:
    return await catalog_call(
        context,
        "get_courses",
        user.faculty_code,
        user.program_code,
        user.level_code,
        user.semester_code,
    )


def remember_reply_message(context: ContextTypes.DEFAULT_TYPE, reply) -> None:
    message_id = getattr(reply, "message_id", None)
    if message_id is not None and hasattr(context, "user_data"):
        context.user_data[ACTIVE_INTERACTIVE_MESSAGE_ID_KEY] = message_id


async def invalidate_quiz_callback_targets(
    context: ContextTypes.DEFAULT_TYPE,
    *,
    user_id: int,
) -> None:
    quiz_service = get_quiz_session_service(context)
    if quiz_service.state_store is None:
        return
    await quiz_service.invalidate_active_callback_targets(user_id=user_id)


async def reply_with_quiz_entry_message(
    *,
    update,
    context: ContextTypes.DEFAULT_TYPE,
    user,
) -> None:
    await invalidate_quiz_callback_targets(
        context,
        user_id=update.effective_user.id,
    )

    if not user_has_complete_profile(user):
        home = get_home_service(context).build_home(
            build_home_profile(user),
            has_active_quiz=getattr(user, "has_active_quiz", False),
        )
        reply = await update.message.reply_text(
            text=build_incomplete_study_profile_message(),
            reply_markup=build_home_keyboard(home["buttons"]),
        )
        remember_reply_message(context, reply)
        return

    courses = await get_profile_courses(context, user)
    if not courses:
        home = get_home_service(context).build_home(
            build_home_profile(user),
            has_active_quiz=getattr(user, "has_active_quiz", False),
        )
        reply = await update.message.reply_text(
            text=build_missing_course_message(),
            reply_markup=build_home_keyboard(home["buttons"]),
        )
        remember_reply_message(context, reply)
        return

    reply = await update.message.reply_text(
        text=build_quiz_course_prompt(
            humanize(getattr(user, "program_code", None), None),
            (
                f"Level {user.level_code}"
                if getattr(user, "level_code", None)
                else None
            ),
        ),
        reply_markup=build_quiz_course_keyboard(courses),
    )
    remember_reply_message(context, reply)
