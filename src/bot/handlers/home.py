from telegram import Update
from telegram.ext import ContextTypes

from src.bot.callbacks import parse_callback
from src.bot.copy import (
    build_help_message,
    build_home_message,
    build_missing_course_message,
    build_performance_placeholder,
    build_quiz_ready_message,
)
from src.bot.handlers.profile_setup import LABEL_KEY, STATE_KEY
from src.domains.quiz.service import QuizSessionService
from src.bot.keyboards import (
    build_home_keyboard,
    build_quiz_length_keyboard,
    build_setup_keyboard,
)
from src.domains.catalog.navigation_service import CatalogNavigationService
from src.domains.home.service import HomeService
from src.domains.profile.service import ProfileService
from src.domains.quiz_entry.service import QuizEntryService


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


def _get_catalog_service(
    context: ContextTypes.DEFAULT_TYPE,
) -> CatalogNavigationService:
    return context.application.bot_data.get(
        "catalog_service", CatalogNavigationService()
    )


def _get_home_service(context: ContextTypes.DEFAULT_TYPE) -> HomeService:
    return context.application.bot_data.get("home_service", HomeService())


def _get_quiz_entry_service(context: ContextTypes.DEFAULT_TYPE) -> QuizEntryService:
    return context.application.bot_data.get("quiz_entry_service", QuizEntryService())


def _get_quiz_session_service(
    context: ContextTypes.DEFAULT_TYPE,
) -> QuizSessionService:
    return context.application.bot_data.get("quiz_session_service", QuizSessionService())


def _get_background_scheduler(context: ContextTypes.DEFAULT_TYPE):
    return context.application.bot_data.get("background_scheduler")


def _noop_schedule(coro) -> None:
    coro.close()


def _get_schedule_background(context: ContextTypes.DEFAULT_TYPE):
    scheduler = _get_background_scheduler(context)
    if scheduler is None:
        return _noop_schedule
    return scheduler.schedule_coroutine


def _course_id(user) -> str:
    return getattr(user, "preferred_course_code", None) or "general-study"


def _course_name(user) -> str:
    return _humanize(getattr(user, "preferred_course_code", None), "Your Course")


def _initial_setup_state() -> dict[str, str | None]:
    return {
        "faculty": None,
        "program": None,
        "level": None,
        "current_step": "faculty",
    }


def _initial_setup_labels() -> dict[str, str | None]:
    return {
        "faculty_name": None,
        "program_name": None,
        "level_name": None,
    }


async def _render_home(query, context: ContextTypes.DEFAULT_TYPE, user) -> None:
    home_service = _get_home_service(context)
    profile = _build_home_profile(user)
    home = home_service.build_home(
        profile,
        has_active_quiz=getattr(user, "has_active_quiz", False),
    )
    await query.edit_message_text(
        text=build_home_message(profile),
        reply_markup=build_home_keyboard(home["buttons"]),
    )


async def _render_study_settings(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data[STATE_KEY] = _initial_setup_state()
    context.user_data[LABEL_KEY] = _initial_setup_labels()
    faculties = _get_catalog_service(context).get_faculties()
    await query.edit_message_text(
        text="Study Profile Setup\n\nChoose your faculty:",
        reply_markup=build_setup_keyboard(
            "faculty",
            faculties,
            include_back=False,
            include_cancel=True,
        ),
    )


async def handle_home_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()

    parts = parse_callback(query.data)
    if not parts:
        return

    profile_service = _get_profile_service(context)
    user = await profile_service.load_or_initialize_user(update.effective_user.id)

    if parts[0] == "home" and len(parts) >= 2:
        action = parts[1]
        quiz_entry_service = _get_quiz_entry_service(context)

        if action == "start_quiz":
            await query.edit_message_text(
                text=quiz_entry_service.build_length_prompt(_course_name(user)),
                reply_markup=build_quiz_length_keyboard(
                    quiz_entry_service.QUESTION_COUNTS
                ),
            )
            return

        if action == "study_settings":
            await _render_study_settings(query, context)
            return

        if action == "continue_quiz":
            resumed = await _get_quiz_session_service(context).continue_quiz(
                bot=context.bot,
                user_id=update.effective_user.id,
            )
            text = (
                "Reopening your active quiz."
                if resumed
                else quiz_entry_service.build_continue_placeholder()
            )
            await query.edit_message_text(
                text=text,
                reply_markup=build_home_keyboard(
                    _get_home_service(context).build_home(
                        _build_home_profile(user),
                        has_active_quiz=getattr(user, "has_active_quiz", False),
                    )["buttons"]
                ),
            )
            return

        if action == "performance":
            await query.edit_message_text(
                text=build_performance_placeholder(),
                reply_markup=build_home_keyboard(
                    _get_home_service(context).build_home(
                        _build_home_profile(user),
                        has_active_quiz=getattr(user, "has_active_quiz", False),
                    )["buttons"]
                ),
            )
            return

        if action == "help":
            await query.edit_message_text(
                text=build_help_message(),
                reply_markup=build_home_keyboard(
                    _get_home_service(context).build_home(
                        _build_home_profile(user),
                        has_active_quiz=getattr(user, "has_active_quiz", False),
                    )["buttons"]
                ),
            )
            return

    if parts[0] == "quiz" and len(parts) >= 3 and parts[1] == "length":
        question_count = int(parts[2])
        await query.edit_message_text(
            text=f"Starting your {question_count}-question quiz for {_course_name(user)}.",
            reply_markup=build_home_keyboard(
                _get_home_service(context).build_home(
                    _build_home_profile(user),
                    has_active_quiz=True,
                )["buttons"]
            ),
        )
        chat = getattr(query, "message", None)
        chat_id = getattr(getattr(chat, "chat", None), "id", None)
        if chat_id is None:
            chat_id = getattr(chat, "chat_id", None)
        if chat_id is None:
            return
        await _get_quiz_session_service(context).start_quiz(
            bot=context.bot,
            user_id=update.effective_user.id,
            chat_id=chat_id,
            course_id=_course_id(user),
            course_name=_course_name(user),
            question_count=question_count,
            schedule_background=_get_schedule_background(context),
        )
