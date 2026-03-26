import inspect
from telegram import Update
from telegram.error import BadRequest
from telegram.ext import ContextTypes

from src.bot.callbacks import parse_callback
from src.bot.keyboards import build_home_keyboard, build_setup_keyboard
from src.domains.catalog.navigation_service import CatalogNavigationService
from src.domains.home.service import HomeService
from src.domains.profile.service import ProfileService
from src.infra.redis.state_store import UserProfileRecord

SETUP_ORDER = ["faculty", "program", "level"]
STATE_KEY = "profile_setup_state"
LABEL_KEY = "profile_setup_labels"
ACTIVE_INTERACTIVE_MESSAGE_ID_KEY = "active_interactive_message_id"


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


async def _maybe_await(value):
    if inspect.isawaitable(value):
        return await value
    return value


async def _catalog_call(context: ContextTypes.DEFAULT_TYPE, method_name: str, *args):
    catalog_service = _get_catalog_service(context)
    method = getattr(catalog_service, method_name)
    return await _maybe_await(method(*args))


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


def _empty_options_message(step: str) -> str:
    if step == "faculty":
        return (
            "Study catalog is unavailable right now, so profile setup cannot continue.\n\n"
            "Please seed or restore the catalog data, then try again."
        )
    return (
        "No study options are available for this step right now.\n\n"
        "Please go back or try again later."
    )


async def _options_for_step(
    context: ContextTypes.DEFAULT_TYPE,
    state: dict[str, str | None],
    step: str,
) -> list[dict]:
    if step == "faculty":
        return await _catalog_call(context, "get_faculties")
    if step == "program":
        return await _catalog_call(context, "get_programs", state["faculty"])
    if step == "level":
        return await _catalog_call(context, "get_levels", state["program"])
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


async def _safe_clear_reply_markup(query) -> None:
    clear_method = getattr(query, "edit_message_reply_markup", None)
    if clear_method is None:
        return
    try:
        await clear_method(reply_markup=None)
    except BadRequest as exc:
        if "Message is not modified" in str(exc):
            return
        raise


def _message_id(query) -> int | None:
    return getattr(getattr(query, "message", None), "message_id", None)


def _remember_active_message(context: ContextTypes.DEFAULT_TYPE, query) -> None:
    message_id = _message_id(query)
    if message_id is not None:
        context.user_data[ACTIVE_INTERACTIVE_MESSAGE_ID_KEY] = message_id


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
        text="This setup menu is out of date. Use the latest message.",
        show_alert=False,
    )
    await _safe_clear_reply_markup(query)
    return True


async def _render_step(query, context: ContextTypes.DEFAULT_TYPE, step: str) -> None:
    state = context.user_data.setdefault(STATE_KEY, _initial_state())
    labels = context.user_data.setdefault(LABEL_KEY, _initial_labels())
    state["current_step"] = step

    options = await _options_for_step(context, state, step)
    if options:
        text = f"{_selection_summary(labels)}\n\n{_prompt_for_step(step)}"
    else:
        text = f"{_selection_summary(labels)}\n\n{_empty_options_message(step)}"
    markup = build_setup_keyboard(
        step,
        options,
        include_back=step != "faculty",
        include_cancel=True,
    )
    await _safe_edit_message_text(query, text=text, reply_markup=markup)
    _remember_active_message(context, query)


async def _complete_setup(
    query, update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    state = context.user_data.get(STATE_KEY, _initial_state())
    labels = context.user_data.get(LABEL_KEY, _initial_labels())
    home_service = _get_home_service(context)
    profile_service = _get_profile_service(context)
    state_store = _get_state_store(context)

    profile_payload = {
        "user_id": update.effective_user.id,
        "display_name": update.effective_user.first_name or update.effective_user.full_name,
        "faculty_code": state["faculty"],
        "program_code": state["program"],
        "level_code": state["level"],
        "semester_code": "first",
        "preferred_course_code": None,
        "onboarding_completed": True,
    }
    persisted_profile = await profile_service.persist_profile_record(profile_payload)
    profile = UserProfileRecord.from_user(persisted_profile, has_active_quiz=False)
    if state_store is not None:
        await state_store.set_user_profile(profile)

    home = home_service.build_home(
        {
            "faculty_name": labels["faculty_name"],
            "program_name": labels["program_name"],
            "level_name": labels["level_name"],
            "semester_name": "First Semester",
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
    _remember_active_message(context, query)


async def handle_profile_setup_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    if await _reject_stale_callback(query, context):
        return
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
    options = await _options_for_step(context, state, action)
    state[action] = selected_code
    labels[f"{action}_name"] = _option_name(options, selected_code)
    _reset_following_steps(state, labels, action)

    current_index = SETUP_ORDER.index(action)
    if current_index == len(SETUP_ORDER) - 1:
        await _complete_setup(query, update, context)
        return

    next_step = SETUP_ORDER[current_index + 1]
    await _render_step(query, context, next_step)
