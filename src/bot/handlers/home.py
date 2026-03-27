import inspect
from telegram import Update
from telegram.error import BadRequest
from telegram.ext import ContextTypes

from src.bot.callbacks import parse_callback
from src.bot.copy import (
    build_help_message,
    build_home_message,
    build_incomplete_study_profile_message,
    build_missing_course_message,
    build_no_questions_available_message,
    build_performance_message,
    build_quiz_course_prompt,
)
from src.bot.handlers.profile_setup import LABEL_KEY, STATE_KEY
from src.domains.quiz.service import NoQuizQuestionsAvailableError, QuizSessionService
from src.bot.keyboards import (
    build_home_keyboard,
    build_quiz_course_keyboard,
    build_quiz_length_keyboard,
    build_setup_keyboard,
)
from src.domains.catalog.navigation_service import CatalogNavigationService
from src.domains.home.service import HomeService
from src.domains.profile.service import ProfileService
from src.domains.performance.service import PerformanceService
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
        "semester_name": _humanize(getattr(user, "semester_code", None), "Not set"),
    }


def _get_profile_service(context: ContextTypes.DEFAULT_TYPE) -> ProfileService:
    return context.application.bot_data.get("profile_service", ProfileService())


def _get_catalog_service(
    context: ContextTypes.DEFAULT_TYPE,
) -> CatalogNavigationService:
    return context.application.bot_data.get(
        "catalog_service", CatalogNavigationService()
    )


async def _maybe_await(value):
    if inspect.isawaitable(value):
        return await value
    return value


async def _catalog_call(context: ContextTypes.DEFAULT_TYPE, method_name: str, *args):
    catalog_service = _get_catalog_service(context)
    method = getattr(catalog_service, method_name)
    return await _maybe_await(method(*args))


def _get_home_service(context: ContextTypes.DEFAULT_TYPE) -> HomeService:
    return context.application.bot_data.get("home_service", HomeService())


def _get_quiz_entry_service(context: ContextTypes.DEFAULT_TYPE) -> QuizEntryService:
    return context.application.bot_data.get("quiz_entry_service", QuizEntryService())


def _get_quiz_session_service(
    context: ContextTypes.DEFAULT_TYPE,
) -> QuizSessionService:
    return context.application.bot_data.get("quiz_session_service", QuizSessionService())


def _get_performance_service(
    context: ContextTypes.DEFAULT_TYPE,
) -> PerformanceService:
    return context.application.bot_data.get("performance_service", PerformanceService())


def _get_background_scheduler(context: ContextTypes.DEFAULT_TYPE):
    return context.application.bot_data.get("background_scheduler")


def _noop_schedule(coro) -> None:
    coro.close()


def _get_schedule_background(context: ContextTypes.DEFAULT_TYPE):
    scheduler = _get_background_scheduler(context)
    if scheduler is None:
        return _noop_schedule
    return scheduler.schedule_coroutine


def _message_id(query) -> int | None:
    return getattr(getattr(query, "message", None), "message_id", None)


def _remember_active_message(context: ContextTypes.DEFAULT_TYPE, query) -> None:
    message_id = _message_id(query)
    if message_id is not None:
        context.user_data[ACTIVE_INTERACTIVE_MESSAGE_ID_KEY] = message_id


async def _safe_clear_reply_markup(query) -> None:
    clear_method = getattr(query, "edit_message_reply_markup", None)
    if clear_method is None:
        return
    try:
        await clear_method(reply_markup=None)
    except BadRequest:
        return


async def _reject_stale_callback(query, context: ContextTypes.DEFAULT_TYPE) -> bool:
    active_message_id = context.user_data.get(ACTIVE_INTERACTIVE_MESSAGE_ID_KEY)
    callback_message_id = _message_id(query)
    if (
        active_message_id is None
        or callback_message_id is None
        or active_message_id == callback_message_id
    ):
        return False

    await query.answer(
        text="This menu is out of date. Use the latest message.",
        show_alert=False,
    )
    await _safe_clear_reply_markup(query)
    return True


def _course_id(user) -> str:
    return getattr(user, "preferred_course_code", None) or "general-study"


def _course_name(user) -> str:
    return _humanize(getattr(user, "preferred_course_code", None), "Your Course")


QUIZ_SELECTION_KEY = "quiz_selection"
ACTIVE_INTERACTIVE_MESSAGE_ID_KEY = "active_interactive_message_id"


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
    _remember_active_message(context, query)


async def _render_study_settings(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data[STATE_KEY] = _initial_setup_state()
    context.user_data[LABEL_KEY] = _initial_setup_labels()
    faculties = await _catalog_call(context, "get_faculties")
    await query.edit_message_text(
        text="Study Profile Setup\n\nChoose your faculty:",
        reply_markup=build_setup_keyboard(
            "faculty",
            faculties,
            include_back=False,
            include_cancel=True,
        ),
    )
    _remember_active_message(context, query)


def _user_has_complete_profile(user) -> bool:
    return all(
        getattr(user, field, None)
        for field in ("faculty_code", "program_code", "level_code", "semester_code")
    )


async def _get_profile_courses(
    context: ContextTypes.DEFAULT_TYPE,
    user,
) -> list[dict[str, str]]:
    return await _catalog_call(
        context,
        "get_courses",
        user.faculty_code,
        user.program_code,
        user.level_code,
        user.semester_code,
    )


def _get_selected_quiz_course(
    context: ContextTypes.DEFAULT_TYPE,
) -> dict[str, str] | None:
    selected = context.user_data.get(QUIZ_SELECTION_KEY)
    if not isinstance(selected, dict):
        return None
    if "course_id" not in selected or "course_name" not in selected:
        return None
    return selected


async def handle_home_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    if await _reject_stale_callback(query, context):
        return
    await query.answer()

    parts = parse_callback(query.data)
    if not parts:
        return

    profile_service = _get_profile_service(context)
    quiz_entry_service = _get_quiz_entry_service(context)
    user = await profile_service.load_or_initialize_user(update.effective_user.id)

    if parts[0] == "home" and len(parts) >= 2:
        action = parts[1]

        if action == "start_quiz":
            if not _user_has_complete_profile(user):
                await query.edit_message_text(
                    text=build_incomplete_study_profile_message(),
                    reply_markup=build_home_keyboard(
                        _get_home_service(context).build_home(
                            _build_home_profile(user),
                            has_active_quiz=getattr(user, "has_active_quiz", False),
                        )["buttons"]
                    ),
                )
                _remember_active_message(context, query)
                return

            courses = await _get_profile_courses(context, user)
            if not courses:
                await query.edit_message_text(
                    text=build_missing_course_message(),
                    reply_markup=build_home_keyboard(
                        _get_home_service(context).build_home(
                            _build_home_profile(user),
                            has_active_quiz=getattr(user, "has_active_quiz", False),
                        )["buttons"]
                    ),
                )
                _remember_active_message(context, query)
                return

            await query.edit_message_text(
                text=build_quiz_course_prompt(
                    _humanize(getattr(user, "program_code", None), None),
                    (
                        f"Level {user.level_code}"
                        if getattr(user, "level_code", None)
                        else None
                    ),
                ),
                reply_markup=build_quiz_course_keyboard(courses),
            )
            _remember_active_message(context, query)
            return

        if action == "back":
            await _render_home(query, context, user)
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
            _remember_active_message(context, query)
            return

        if action == "performance":
            performance_summary = await _get_performance_service(context).get_summary(
                update.effective_user.id
            )
            await query.edit_message_text(
                text=build_performance_message(performance_summary),
                reply_markup=build_home_keyboard(
                    _get_home_service(context).build_home(
                        _build_home_profile(user),
                        has_active_quiz=getattr(user, "has_active_quiz", False),
                    )["buttons"]
                ),
            )
            _remember_active_message(context, query)
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
            _remember_active_message(context, query)
            return

    if parts[0] == "quiz" and len(parts) >= 3 and parts[1] == "course":
        course_code = parts[2]
        selected_course = next(
            (
                course
                for course in await _get_profile_courses(context, user)
                if course["code"] == course_code
            ),
            None,
        )
        if selected_course is None:
            await query.edit_message_text(
                text=build_missing_course_message(),
                reply_markup=build_home_keyboard(
                    _get_home_service(context).build_home(
                        _build_home_profile(user),
                        has_active_quiz=getattr(user, "has_active_quiz", False),
                    )["buttons"]
                ),
            )
            _remember_active_message(context, query)
            return

        context.user_data[QUIZ_SELECTION_KEY] = {
            "course_id": selected_course["code"],
            "course_name": selected_course["name"],
        }
        await query.edit_message_text(
            text=quiz_entry_service.build_length_prompt(selected_course["name"]),
            reply_markup=build_quiz_length_keyboard(
                quiz_entry_service.QUESTION_COUNTS
            ),
        )
        _remember_active_message(context, query)
        return

    if parts[0] == "quiz" and len(parts) >= 3 and parts[1] == "length":
        question_count = int(parts[2])
        selected_course = _get_selected_quiz_course(context)
        if selected_course is None:
            await query.edit_message_text(
                text=build_missing_course_message(),
                reply_markup=build_home_keyboard(
                    _get_home_service(context).build_home(
                        _build_home_profile(user),
                        has_active_quiz=getattr(user, "has_active_quiz", False),
                    )["buttons"]
                ),
            )
            _remember_active_message(context, query)
            return

        await query.edit_message_text(
            text=(
                f"Starting your {question_count}-question quiz for "
                f"{selected_course['course_name']}."
            ),
            reply_markup=build_home_keyboard(
                _get_home_service(context).build_home(
                    _build_home_profile(user),
                    has_active_quiz=True,
                )["buttons"]
            ),
        )
        _remember_active_message(context, query)
        chat = getattr(query, "message", None)
        chat_id = getattr(getattr(chat, "chat", None), "id", None)
        if chat_id is None:
            chat_id = getattr(chat, "chat_id", None)
        if chat_id is None:
            return
        try:
            await _get_quiz_session_service(context).start_quiz(
                bot=context.bot,
                user_id=update.effective_user.id,
                chat_id=chat_id,
                course_id=selected_course["course_id"],
                course_name=selected_course["course_name"],
                question_count=question_count,
                schedule_background=_get_schedule_background(context),
            )
        except NoQuizQuestionsAvailableError:
            await query.edit_message_text(
                text=build_no_questions_available_message(
                    selected_course["course_name"]
                ),
                reply_markup=build_home_keyboard(
                    _get_home_service(context).build_home(
                        _build_home_profile(user),
                        has_active_quiz=getattr(user, "has_active_quiz", False),
                    )["buttons"]
                ),
            )
            _remember_active_message(context, query)
