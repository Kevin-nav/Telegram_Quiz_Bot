from __future__ import annotations

import logging
from uuid import uuid4

from telegram import PollAnswer

from src.domains.quiz.models import PollMapRecord, QuizQuestion, QuizSessionState
from src.infra.redis.state_store import InteractiveStateStore
from src.tasks.arq_client import (
    enqueue_generate_quiz_session,
    enqueue_persist_quiz_attempt,
    enqueue_persist_quiz_session_progress,
)


logger = logging.getLogger(__name__)


class QuizSessionService:
    def __init__(self, state_store: InteractiveStateStore | None = None):
        self.state_store = state_store

    def set_state_store(self, state_store: InteractiveStateStore) -> None:
        self.state_store = state_store

    async def start_quiz(
        self,
        *,
        bot,
        user_id: int,
        chat_id: int,
        course_id: str,
        course_name: str,
        question_count: int,
        schedule_background,
    ) -> QuizSessionState:
        self._require_state_store()

        questions = await self._select_questions(course_id, course_name, question_count)
        session = QuizSessionState(
            session_id=str(uuid4()),
            user_id=user_id,
            chat_id=chat_id,
            course_id=course_id,
            course_name=course_name,
            questions=questions,
        )
        await self.state_store.set_quiz_session(session)
        await self.state_store.set_active_quiz(user_id, session.session_id)

        schedule_background(
            enqueue_generate_quiz_session(
                {
                    "session_id": session.session_id,
                    "user_id": user_id,
                    "course_id": course_id,
                    "question_count": question_count,
                }
            )
        )

        await self._send_current_question(session, bot=bot)
        return session

    async def continue_quiz(self, *, bot, user_id: int) -> bool:
        self._require_state_store()

        session_id = await self.state_store.get_active_quiz(user_id)
        if not session_id:
            return False

        session = await self.state_store.get_quiz_session(session_id)
        if session is None or session.status != "active":
            return False

        if session.current_poll_id:
            await bot.send_message(
                chat_id=session.chat_id,
                text=(
                    f"Your {session.course_name} quiz is still active. "
                    "Answer the current poll to continue."
                ),
            )
            return True

        await self._send_current_question(session, bot=bot)
        return True

    async def handle_poll_answer(
        self,
        *,
        bot,
        poll_answer: PollAnswer,
        schedule_background,
    ) -> bool:
        self._require_state_store()

        poll_map = await self.state_store.get_poll_map(poll_answer.poll_id)
        if poll_map is None:
            logger.warning("Received poll answer for unknown poll_id=%s.", poll_answer.poll_id)
            return False

        lock_token = await self.state_store.acquire_quiz_lock(poll_map.session_id)
        if lock_token is None:
            logger.info(
                "Quiz session %s is already being processed; skipping duplicate poll answer.",
                poll_map.session_id,
            )
            return True

        try:
            session = await self.state_store.get_quiz_session(poll_map.session_id)
            if session is None or session.status != "active":
                return False

            question = session.current_question()
            if question is None:
                return False

            selected_option_ids = list(poll_answer.option_ids or [])
            is_correct = question.correct_option_id in selected_option_ids
            if is_correct:
                session.score += 1

            session.current_poll_id = None
            session.current_index += 1

            schedule_background(
                enqueue_persist_quiz_attempt(
                    {
                        "session_id": session.session_id,
                        "user_id": session.user_id,
                        "course_id": session.course_id,
                        "question_id": question.question_id,
                        "question_index": poll_map.question_index,
                        "selected_option_ids": selected_option_ids,
                        "correct_option_id": question.correct_option_id,
                        "is_correct": is_correct,
                    }
                )
            )

            if session.current_index >= session.total_questions:
                session.status = "completed"
                await self.state_store.set_quiz_session(session)
                await self.state_store.clear_active_quiz(session.user_id)
                await bot.send_message(
                    chat_id=session.chat_id,
                    text=(
                        f"Quiz complete for {session.course_name}.\n\n"
                        f"Score: {session.score}/{session.total_questions}"
                    ),
                )
                schedule_background(
                    enqueue_persist_quiz_session_progress(
                        {
                            "session_id": session.session_id,
                            "user_id": session.user_id,
                            "course_id": session.course_id,
                            "status": session.status,
                            "score": session.score,
                            "total_questions": session.total_questions,
                        }
                    )
                )
                return True

            await self.state_store.set_quiz_session(session)
            await self._send_current_question(session, bot=bot)
            schedule_background(
                enqueue_persist_quiz_session_progress(
                    {
                        "session_id": session.session_id,
                        "user_id": session.user_id,
                        "course_id": session.course_id,
                        "status": session.status,
                        "current_index": session.current_index,
                        "score": session.score,
                    }
                )
            )
            return True
        finally:
            await self.state_store.release_quiz_lock(poll_map.session_id, lock_token)

    async def _send_current_question(self, session: QuizSessionState, *, bot) -> None:
        question = session.current_question()
        if question is None:
            return

        message = await bot.send_poll(
            chat_id=session.chat_id,
            question=question.prompt,
            options=question.options,
            type="quiz",
            is_anonymous=False,
            correct_option_id=question.correct_option_id,
        )
        session.current_poll_id = message.poll.id
        await self.state_store.set_quiz_session(session)
        await self.state_store.set_poll_map(
            PollMapRecord(
                poll_id=message.poll.id,
                session_id=session.session_id,
                question_id=question.question_id,
                question_index=session.current_index,
                user_id=session.user_id,
            )
        )

    async def _select_questions(
        self, course_id: str, course_name: str, question_count: int
    ) -> list[QuizQuestion]:
        cached_questions = await self.state_store.get_question_bank(course_id)
        if cached_questions is None or len(cached_questions) < question_count:
            cached_questions = self._build_placeholder_questions(course_name, max(question_count, 30))
            await self.state_store.cache_question_bank(course_id, cached_questions)
        return cached_questions[:question_count]

    def _build_placeholder_questions(
        self, course_name: str, question_count: int
    ) -> list[QuizQuestion]:
        questions: list[QuizQuestion] = []
        for index in range(question_count):
            correct_option = index % 4
            options = [
                "Review core idea",
                "Apply the concept",
                "Check the hidden assumption",
                "Revisit the worked example",
            ]
            questions.append(
                QuizQuestion(
                    question_id=f"{course_name.lower().replace(' ', '-')}-{index + 1}",
                    prompt=f"{course_name}: question {index + 1}",
                    options=options,
                    correct_option_id=correct_option,
                    explanation="Placeholder quiz content until the adaptive selector is connected.",
                )
            )
        return questions

    def _require_state_store(self) -> None:
        if self.state_store is None:
            raise RuntimeError("QuizSessionService requires an InteractiveStateStore.")
