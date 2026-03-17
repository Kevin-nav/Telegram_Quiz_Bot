from telegram import Update
from telegram.ext import ContextTypes

from src.bot.callbacks import parse_callback
from src.bot.handlers.profile_setup import LABEL_KEY, STATE_KEY
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
            f"Level {user.level_code}" if getattr(user, "level_code", None) else "Not set"
        ),
        "semester_name": _humanize(getattr(user, "semester_code", None), "Not set"),
        "course_name": _humanize(
            getattr(user, "preferred_course_code", None), "No course selected"
        ),
    }


def _get_profile_service(context: ContextTypes.DEFAULT_TYPE) -> ProfileService:
    return context.application.bot_data.get("profile_service", ProfileService())


def _get_catalog_service(context: ContextTypes.DEFAULT_TYPE) -> CatalogNavigationService:
    return context.application.bot_data.get(
        "catalog_service", CatalogNavigationService()
    )


def _get_home_service(context: ContextTypes.DEFAULT_TYPE) -> HomeService:
    return context.application.bot_data.get("home_service", HomeService())


def _get_quiz_entry_service(context: ContextTypes.DEFAULT_TYPE) -> QuizEntryService:
    return context.application.bot_data.get("quiz_entry_service", QuizEntryService())


def _initial_setup_state() -> dict[str, str | None]:
    return {
        "faculty": None,
        "program": None,
        "level": None,
        "semester": None,
        "course": None,
        "current_step": "faculty",
    }


def _initial_setup_labels() -> dict[str, str | None]:
    return {
        "faculty_name": None,
        "program_name": None,
        "level_name": None,
        "semester_name": None,
        "course_name": None,
    }


async def _render_home(query, context: ContextTypes.DEFAULT_TYPE, user) -> None:
    home_service = _get_home_service(context)
    home = home_service.build_home(
        _build_home_profile(user),
        has_active_quiz=getattr(user, "has_active_quiz", False),
    )
    await query.edit_message_text(
        text=home["message"],
        reply_markup=build_home_keyboard(home["buttons"]),
    )


async def _render_change_course(query, context: ContextTypes.DEFAULT_TYPE) -> None:
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


async def handle_home_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
            course_name = _build_home_profile(user)["course_name"]
            if course_name == "No course selected":
                await query.edit_message_text(
                    text="Choose your course first so the bot knows where to start.",
                    reply_markup=build_home_keyboard(
                        _get_home_service(context).build_home(
                            _build_home_profile(user),
                            has_active_quiz=getattr(user, "has_active_quiz", False),
                        )["buttons"]
                    ),
                )
                return

            await query.edit_message_text(
                text=quiz_entry_service.build_length_prompt(course_name),
                reply_markup=build_quiz_length_keyboard(
                    quiz_entry_service.QUESTION_COUNTS
                ),
            )
            return

        if action == "change_course" or action == "study_settings":
            await _render_change_course(query, context)
            return

        if action == "continue_quiz":
            await query.edit_message_text(
                text=quiz_entry_service.build_continue_placeholder(),
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
                text=quiz_entry_service.build_performance_placeholder(),
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
                text=quiz_entry_service.build_help_message(),
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
        course_name = _build_home_profile(user)["course_name"]
        await query.edit_message_text(
            text=_get_quiz_entry_service(context).build_quiz_ready_message(
                course_name,
                question_count,
            ),
            reply_markup=build_home_keyboard(
                _get_home_service(context).build_home(
                    _build_home_profile(user),
                    has_active_quiz=getattr(user, "has_active_quiz", False),
                )["buttons"]
            ),
        )
