import logging

from telegram import Update
from telegram.ext import ContextTypes

from src.domains.quiz.service import QuizSessionService


logger = logging.getLogger(__name__)


def _get_quiz_session_service(
    context: ContextTypes.DEFAULT_TYPE,
) -> QuizSessionService:
    return context.application.bot_data.get("quiz_session_service", QuizSessionService())


def _get_background_scheduler(context: ContextTypes.DEFAULT_TYPE):
    return context.application.bot_data.get("background_scheduler")


def _noop_schedule(coro) -> None:
    coro.close()


async def handle_poll_answer(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    poll_answer = update.poll_answer
    if poll_answer is None:
        return

    service = _get_quiz_session_service(context)
    scheduler = _get_background_scheduler(context)
    schedule_background = (
        scheduler.schedule_coroutine if scheduler is not None else _noop_schedule
    )
    handled = await service.handle_poll_answer(
        bot=context.bot,
        poll_answer=poll_answer,
        schedule_background=schedule_background,
    )
    if not handled:
        logger.warning(
            "Poll answer was not handled for poll_id=%s.",
            poll_answer.poll_id,
        )
