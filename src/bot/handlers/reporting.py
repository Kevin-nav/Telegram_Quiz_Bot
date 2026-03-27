from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from src.bot.callbacks import parse_callback
from src.bot.copy import (
    build_answer_action_prompt,
    build_question_action_prompt,
    build_report_cancelled_message,
    build_report_confirmation_message,
    build_report_note_prompt,
    build_report_reason_prompt,
)
from src.bot.keyboards import (
    build_answer_action_keyboard,
    build_question_action_keyboard,
    build_report_note_keyboard,
    build_report_reason_keyboard,
)
from src.domains.quiz.service import QuizSessionService
from src.domains.quiz_reporting.service import QuizReportingService
from src.tasks.arq_client import enqueue_persist_question_report


QUESTION_REASON_OPTIONS = [
    ("Not related to course", "not_related_to_course"),
    ("Question unclear", "question_unclear"),
    ("Image/LaTeX issue", "image_or_latex_issue"),
    ("Duplicate question", "duplicate_question"),
    ("Other", "other"),
]

ANSWER_REASON_OPTIONS = [
    ("Marked wrong but my answer is right", "marked_wrong_but_my_answer_is_right"),
    ("Correct answer shown is wrong", "correct_answer_shown_is_wrong"),
    ("Explanation is wrong", "explanation_is_wrong"),
    ("Other", "other"),
]


def _get_quiz_session_service(
    context: ContextTypes.DEFAULT_TYPE,
) -> QuizSessionService:
    return context.application.bot_data.get("quiz_session_service", QuizSessionService())


def _get_reporting_service(context: ContextTypes.DEFAULT_TYPE) -> QuizReportingService:
    return context.application.bot_data.get(
        "quiz_reporting_service", QuizReportingService()
    )


def _get_background_scheduler(context: ContextTypes.DEFAULT_TYPE):
    return context.application.bot_data.get("background_scheduler")


def _noop_schedule(coro) -> None:
    coro.close()


def _schedule_background(context: ContextTypes.DEFAULT_TYPE):
    scheduler = _get_background_scheduler(context)
    if scheduler is None:
        return _noop_schedule
    return scheduler.schedule_coroutine


async def _load_active_session(context: ContextTypes.DEFAULT_TYPE, user_id: int):
    quiz_service = _get_quiz_session_service(context)
    store = quiz_service.state_store
    if store is None:
        return None, None
    session_id = await store.get_active_quiz(user_id)
    if not session_id:
        return store, None
    return store, await store.get_quiz_session(session_id)


def _expected_message_id_for_scope(session, scope: str) -> int | None:
    if scope == "question":
        return session.question_action_message_id
    return session.answer_action_message_id


async def _reject_stale_report_callback(query, session, scope: str) -> bool:
    expected_message_id = _expected_message_id_for_scope(session, scope)
    callback_message_id = getattr(getattr(query, "message", None), "message_id", None)
    if expected_message_id is None or callback_message_id == expected_message_id:
        return False

    await query.answer(
        text="This report menu is out of date. Use the latest one.",
        show_alert=False,
    )
    clear_method = getattr(query, "edit_message_reply_markup", None)
    if clear_method is not None:
        await clear_method(reply_markup=None)
    return True


def _reason_options(scope: str) -> list[tuple[str, str]]:
    return QUESTION_REASON_OPTIONS if scope == "question" else ANSWER_REASON_OPTIONS


async def _restore_action_prompt(query, scope: str) -> None:
    if scope == "question":
        await query.edit_message_text(
            text=build_question_action_prompt(),
            reply_markup=build_question_action_keyboard(),
        )
        return

    await query.edit_message_text(
        text=build_answer_action_prompt(),
        reply_markup=build_answer_action_keyboard(),
    )


async def handle_report_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()

    parts = parse_callback(query.data)
    if len(parts) < 3 or parts[0] != "report":
        return

    action = parts[1]
    scope = parts[2]
    store, session = await _load_active_session(context, update.effective_user.id)
    if store is None or session is None:
        return
    if await _reject_stale_report_callback(query, session, scope):
        return

    reporting_service = _get_reporting_service(context)

    if action == "start":
        await query.edit_message_text(
            text=build_report_reason_prompt(scope),
            reply_markup=build_report_reason_keyboard(scope, _reason_options(scope)),
        )
        return

    if action == "reason" and len(parts) >= 4:
        reason = parts[3]
        payload = reporting_service.build_report_payload(
            session=session,
            report_scope=scope,
            report_reason=reason,
            report_note=None,
        )
        await store.set_report_draft(update.effective_user.id, payload)
        await store.set_pending_report_note(update.effective_user.id, payload)
        await query.edit_message_text(
            text=build_report_note_prompt(scope),
            reply_markup=build_report_note_keyboard(scope),
        )
        return

    if action == "skip_note":
        payload = await store.get_pending_report_note(update.effective_user.id)
        if payload is None:
            return
        _schedule_background(context)(enqueue_persist_question_report(payload))
        await store.clear_pending_report_note(update.effective_user.id)
        await store.clear_report_draft(update.effective_user.id)
        await query.edit_message_text(text=build_report_confirmation_message())
        return

    if action == "cancel":
        await store.clear_pending_report_note(update.effective_user.id)
        await store.clear_report_draft(update.effective_user.id)
        await query.edit_message_text(text=build_report_cancelled_message())
        await _restore_action_prompt(query, scope)


async def handle_report_note_message(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    store, _ = await _load_active_session(context, update.effective_user.id)
    if store is None:
        return

    payload = await store.get_pending_report_note(update.effective_user.id)
    if payload is None:
        return

    text = getattr(update.effective_message, "text", None)
    if not text:
        await update.effective_message.reply_text(
            "Send your report note as text, or use Skip note."
        )
        return

    payload["report_note"] = text.strip()
    _schedule_background(context)(enqueue_persist_question_report(payload))
    await store.clear_pending_report_note(update.effective_user.id)
    await store.clear_report_draft(update.effective_user.id)
    await update.effective_message.reply_text(build_report_confirmation_message())
