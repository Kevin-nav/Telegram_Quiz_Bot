from telegram import Update
from telegram.error import BadRequest
from telegram.ext import ContextTypes

from src.bot.callbacks import parse_callback
from src.bot.keyboards import build_home_keyboard, build_setup_keyboard
from src.domains.catalog.navigation_service import CatalogNavigationService
from src.domains.home.service import HomeService
from src.domains.profile.service import ProfileService
from src.infra.redis.state_store import UserProfileRecord
from src.tasks.arq_client import enqueue_persist_user_profile

SETUP_ORDER = ["faculty", "program", "level"]
STATE_KEY = "profile_setup_state"
LABEL_KEY = "profile_setup_labels"


def _humanize(code: str | None) -> str:
    if not code:
        return "Not set"
    return code.replace("-", " ").title()


def _get_catalog_service(
    context: ContextTypes.DEFAULT_TYPE,
) -> CatalogNavigationService:
    return context.application.bot_data.get(
        "catalog_service", CatalogNavigationService()
    )


def _get_profile_service(context: ContextTypes.DEFAULT_TYPE) -> ProfileService:
    return context.application.bot_data.get("profile_service", ProfileService())


def _get_home_service(context: ContextTypes.DEFAULT_TYPE) -> HomeService:
    return context.application.bot_data.get("home_service", HomeService())


def _get_state_store(context: ContextTypes.DEFAULT_TYPE):
    return context.application.bot_data.get("state_store")


def _get_background_scheduler(context: ContextTypes.DEFAULT_TYPE):
    return context.application.bot_data.get("background_scheduler")


def _initial_state() -> dict[str, str | None]:
    return {
        "faculty": None,
        "program": None,
        "level": None,
        "current_step": "faculty",
    }


def _initial_labels() -> dict[str, str | None]:
    return {
        "faculty_name": None,
        "program_name": None,
        "level_name": None,
    }


def _reset_following_steps(
    state: dict[str, str | None], labels: dict[str, str | None], step: str
) -> None:
    start_index = SETUP_ORDER.index(step)
    for later_step in SETUP_ORDER[start_index + 1 :]:
        state[later_step] = None
        labels[f"{later_step}_name"] = None


def _selection_summary(labels: dict[str, str | None]) -> str:
    return (
        "Study Profile Setup\n\n"
        f"Faculty: {labels.get('faculty_name') or 'Not set'}\n"
        f"Program: {labels.get('program_name') or 'Not set'}\n"
        f"Level: {labels.get('level_name') or 'Not set'}"
    )


def _prompt_for_step(step: str) -> str:
    return {
        "faculty": "Choose your faculty:",
        "program": "Choose your program:",
        "level": "Choose your level:",
    }[step]


def _options_for_step(
    catalog_service: CatalogNavigationService,
    state: dict[str, str | None],
    step: str,
) -> list[dict]:
    if step == "faculty":
        return catalog_service.get_faculties()
    if step == "program":
        return catalog_service.get_programs(state["faculty"])
    if step == "level":
        return catalog_service.get_levels(state["program"])
    return []


def _option_name(options: list[dict], code: str) -> str:
    for option in options:
        if option["code"] == code:
            return option["name"]
    return _humanize(code)


async def _safe_edit_message_text(query, *, text: str, reply_markup=None) -> None:
    try:
        await query.edit_message_text(text=text, reply_markup=reply_markup)
    except BadRequest as exc:
        if "Message is not modified" in str(exc):
            return
        raise


async def _render_step(query, context: ContextTypes.DEFAULT_TYPE, step: str) -> None:
    state = context.user_data.setdefault(STATE_KEY, _initial_state())
    labels = context.user_data.setdefault(LABEL_KEY, _initial_labels())
    state["current_step"] = step

    options = _options_for_step(_get_catalog_service(context), state, step)
    text = f"{_selection_summary(labels)}\n\n{_prompt_for_step(step)}"
    markup = build_setup_keyboard(
        step,
        options,
        include_back=step != "faculty",
        include_cancel=True,
    )
    await _safe_edit_message_text(query, text=text, reply_markup=markup)


async def _complete_setup(
    query, update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    state = context.user_data.get(STATE_KEY, _initial_state())
    labels = context.user_data.get(LABEL_KEY, _initial_labels())
    home_service = _get_home_service(context)
    state_store = _get_state_store(context)
    scheduler = _get_background_scheduler(context)

    profile = UserProfileRecord(
        id=update.effective_user.id,
        display_name=update.effective_user.first_name or update.effective_user.full_name,
        faculty_code=state["faculty"],
        program_code=state["program"],
        level_code=state["level"],
        semester_code=None,
        preferred_course_code=None,
        onboarding_completed=True,
    )
    if state_store is not None:
        await state_store.set_user_profile(profile)

    home = home_service.build_home(
        {
            "faculty_name": labels["faculty_name"],
            "program_name": labels["program_name"],
            "level_name": labels["level_name"],
            "semester_name": None,
            "course_name": None,
        },
        has_active_quiz=False,
    )
    context.user_data.pop(STATE_KEY, None)
    context.user_data.pop(LABEL_KEY, None)
    await _safe_edit_message_text(
        query,
        text=home["message"],
        reply_markup=build_home_keyboard(home["buttons"]),
    )
    if scheduler is not None:
        scheduler.schedule_coroutine(
            enqueue_persist_user_profile(
                {
                    "user_id": profile.id,
                    "display_name": profile.display_name,
                    "faculty_code": profile.faculty_code,
                    "program_code": profile.program_code,
                    "level_code": profile.level_code,
                    "semester_code": profile.semester_code,
                    "preferred_course_code": profile.preferred_course_code,
                    "onboarding_completed": True,
                }
            )
        )


async def handle_profile_setup_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()

    parts = parse_callback(query.data)
    if len(parts) < 2 or parts[0] != "profile":
        return

    action = parts[1]
    state = context.user_data.setdefault(STATE_KEY, _initial_state())
    labels = context.user_data.setdefault(LABEL_KEY, _initial_labels())

    if action == "start":
        context.user_data[STATE_KEY] = _initial_state()
        context.user_data[LABEL_KEY] = _initial_labels()
        await _render_step(query, context, "faculty")
        return

    if action == "cancel":
        context.user_data.pop(STATE_KEY, None)
        context.user_data.pop(LABEL_KEY, None)
        await _safe_edit_message_text(query, text="Study profile setup cancelled.")
        return

    if action == "back":
        current_step = state["current_step"] or "faculty"
        current_index = SETUP_ORDER.index(current_step)
        previous_step = SETUP_ORDER[max(0, current_index - 1)]
        state[current_step] = None
        labels[f"{current_step}_name"] = None
        await _render_step(query, context, previous_step)
        return

    if len(parts) < 3 or action not in SETUP_ORDER:
        return

    selected_code = parts[2]
    options = _options_for_step(_get_catalog_service(context), state, action)
    state[action] = selected_code
    labels[f"{action}_name"] = _option_name(options, selected_code)
    _reset_following_steps(state, labels, action)

    current_index = SETUP_ORDER.index(action)
    if current_index == len(SETUP_ORDER) - 1:
        await _complete_setup(query, update, context)
        return

    next_step = SETUP_ORDER[current_index + 1]
    await _render_step(query, context, next_step)
