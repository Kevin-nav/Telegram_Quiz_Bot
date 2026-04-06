from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import uuid4

from telegram import PollAnswer

from src.bot.copy import (
    build_answer_action_prompt,
    build_question_action_prompt,
    build_quiz_completion_message,
)
from src.bot.runtime_config import TANJAH_BOT_ID
from src.bot.keyboards import (
    build_answer_action_keyboard,
    build_question_action_keyboard,
)
from src.domains.adaptive.arrangement import (
    arrange_options_latex,
    arrange_options_non_latex,
)
from src.domains.adaptive.models import AdaptiveQuestionProfile
from src.domains.adaptive.service import AdaptiveLearningService
from src.domains.adaptive.timing import calculate_question_time_limit
from src.domains.quiz.models import PollMapRecord, QuizQuestion, QuizSessionState
from src.infra.db.repositories.question_bank_repository import QuestionBankRepository
from src.infra.redis.state_store import InteractiveStateStore
from src.tasks.arq_client import (
    enqueue_generate_quiz_session,
    enqueue_persist_quiz_attempt,
    enqueue_persist_quiz_session_progress,
)


logger = logging.getLogger(__name__)


class NoQuizQuestionsAvailableError(Exception):
    pass


class QuizSessionService:
    def __init__(
        self,
        state_store: InteractiveStateStore | None = None,
        question_bank_repository: QuestionBankRepository | None = None,
        adaptive_learning_service: AdaptiveLearningService | None = None,
        bot_id: str = TANJAH_BOT_ID,
    ):
        self.state_store = state_store
        self.bot_id = bot_id
        self.question_bank_repository = question_bank_repository or QuestionBankRepository()
        self.adaptive_learning_service = (
            adaptive_learning_service
            or AdaptiveLearningService(question_bank_repository=self.question_bank_repository)
        )

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

        questions = await self._select_questions(
            user_id=user_id,
            course_id=course_id,
            course_name=course_name,
            question_count=question_count,
        )
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
                    "bot_id": self.bot_id,
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

    async def invalidate_active_callback_targets(self, *, user_id: int) -> bool:
        self._require_state_store()

        session_id = await self.state_store.get_active_quiz(user_id)
        if not session_id:
            return False

        session = await self.state_store.get_quiz_session(session_id)
        if session is None:
            return False

        session.question_action_message_id = None
        session.answer_action_message_id = None
        await self.state_store.set_quiz_session(session)
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
            selected_option_text = None
            if selected_option_ids:
                selected_index = selected_option_ids[0]
                if 0 <= selected_index < len(question.options):
                    selected_option_text = question.options[selected_index]
            time_taken_seconds = None
            if question.presented_at is not None:
                time_taken_seconds = (
                    datetime.now(UTC) - question.presented_at
                ).total_seconds()
            if is_correct:
                session.score += 1

            question.selected_option_ids = selected_option_ids
            question.selected_option_text = selected_option_text
            question.was_answered_correctly = is_correct
            question.time_taken_seconds = time_taken_seconds
            session.current_poll_id = None

            schedule_background(
                enqueue_persist_quiz_attempt(
                    {
                        "session_id": session.session_id,
                        "user_id": session.user_id,
                        "bot_id": self.bot_id,
                        "course_id": session.course_id,
                        "question_id": question.question_id,
                        "source_question_id": question.source_question_id,
                        "question_index": poll_map.question_index,
                        "selected_option_ids": selected_option_ids,
                        "selected_option_text": selected_option_text,
                        "correct_option_id": question.correct_option_id,
                        "is_correct": is_correct,
                        "arrangement_hash": question.arrangement_hash,
                        "config_index": question.config_index,
                        "time_taken_seconds": time_taken_seconds,
                        "time_allocated_seconds": question.time_allocated_seconds,
                        "metadata": {
                            "topic_id": question.topic_id,
                            "scaled_score": question.scaled_score,
                            "band": question.band,
                            "cognitive_level": question.cognitive_level,
                            "question_type": "MCQ",
                            "option_count": len(question.options),
                            "processing_complexity": question.processing_complexity,
                            "distractor_complexity": question.distractor_complexity,
                            "note_reference": question.note_reference,
                            "has_latex": question.has_latex,
                            "question_asset_url": question.question_asset_url,
                            "explanation_asset_url": question.explanation_asset_url,
                            "presented_at": (
                                question.presented_at.isoformat()
                                if question.presented_at is not None
                                else None
                            ),
                            "selected_option_text": selected_option_text,
                            "selected_option_ids": selected_option_ids,
                        },
                    }
                )
            )

            await self._send_answer_feedback(
                session,
                question=question,
                is_correct=is_correct,
                bot=bot,
            )
            session.last_answered_question_id = question.question_id
            session.last_answered_question_index = poll_map.question_index
            await self._send_answer_actions(session, bot=bot)

            session.current_index += 1

            if session.current_index >= session.total_questions:
                session.status = "completed"
                await self.state_store.set_quiz_session(session)
                await self.state_store.clear_active_quiz(session.user_id)
                await bot.send_message(
                    chat_id=session.chat_id,
                    text=build_quiz_completion_message(
                        self._build_completion_summary(session)
                    ),
                )
                schedule_background(
                    enqueue_persist_quiz_session_progress(
                        {
                            "session_id": session.session_id,
                            "user_id": session.user_id,
                            "bot_id": self.bot_id,
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
                        "bot_id": self.bot_id,
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

        if question.presented_at is None:
            question.presented_at = datetime.now(UTC)
        if question.time_allocated_seconds is None:
            question.time_allocated_seconds = self._calculate_time_allocated_seconds(
                question
            )

        question_text = question.prompt
        poll_options = question.options
        await bot.send_message(
            chat_id=session.chat_id,
            text=self._build_question_progress_text(session),
        )
        if question.has_latex:
            if question.question_asset_url:
                await bot.send_photo(
                    chat_id=session.chat_id,
                    photo=question.question_asset_url,
                )
            question_text = "Choose the correct option."
            poll_options = self._latex_poll_options(question)

        message = await bot.send_poll(
            chat_id=session.chat_id,
            question=question_text,
            options=poll_options,
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
        action_message = await self._send_action_message(
            bot=bot,
            chat_id=session.chat_id,
            text=build_question_action_prompt(),
            reply_markup=build_question_action_keyboard(),
        )
        session.question_action_message_id = getattr(action_message, "message_id", None)
        await self.state_store.set_quiz_session(session)

    async def _select_questions(
        self,
        *,
        user_id: int | None = None,
        course_id: str,
        course_name: str,
        question_count: int,
    ) -> list[QuizQuestion]:
        try:
            selection = await self.adaptive_learning_service.select_questions(
                user_id=user_id or 0,
                bot_id=self.bot_id,
                course_id=course_id,
                quiz_length=question_count,
            )
        except Exception as exc:
            logger.exception(
                "Failed to load adaptive questions for course_id=%s.",
                course_id,
            )
            raise NoQuizQuestionsAvailableError(course_id) from exc

        question_rows_by_key = {
            row.question_key: row for row in selection.question_rows if hasattr(row, "question_key")
        }
        quiz_questions: list[QuizQuestion] = []
        for selected_question in selection.selected_questions:
            question_row = question_rows_by_key.get(selected_question.question_id)
            if question_row is None:
                continue
            try:
                quiz_question = self._build_quiz_question(
                    question_row,
                    selected_question,
                )
            except ValueError:
                logger.warning(
                    "Skipping malformed canonical question %s during adaptive selection.",
                    selected_question.question_id,
                )
                continue
            quiz_questions.append(quiz_question)

        if quiz_questions:
            return quiz_questions[:question_count]

        logger.warning(
            "Adaptive selector returned no canonical questions for course_id=%s.",
            course_id,
        )
        raise NoQuizQuestionsAvailableError(course_id)

    async def _send_answer_feedback(
        self,
        session: QuizSessionState,
        *,
        question: QuizQuestion,
        is_correct: bool,
        bot,
    ) -> None:
        if question.has_latex:
            await bot.send_message(
                chat_id=session.chat_id,
                text=self._build_feedback_text(question, is_correct=is_correct),
            )
            if question.explanation_asset_url:
                await bot.send_photo(
                    chat_id=session.chat_id,
                    photo=question.explanation_asset_url,
                )
            elif question.explanation:
                await bot.send_message(
                    chat_id=session.chat_id,
                    text=question.explanation,
                )
            return

        await bot.send_message(
            chat_id=session.chat_id,
            text=self._build_feedback_with_explanation_text(
                question,
                is_correct=is_correct,
            ),
        )

    def _build_quiz_question(
        self,
        question_row,
        selected_question: AdaptiveQuestionProfile,
    ) -> QuizQuestion:
        if question_row.correct_option_text not in question_row.options:
            raise ValueError(
                f"Question {question_row.question_key} has an invalid correct option."
            )

        options = list(question_row.options)
        correct_option_id = options.index(question_row.correct_option_text)
        arrangement_hash = None
        config_index = selected_question.config_index
        question_asset_url = getattr(question_row, "question_asset_url", None)

        if question_row.has_latex:
            if config_index is None:
                config_index = arrange_options_latex(selected_question)
            question_asset_url, correct_option_id = self._resolve_latex_variant(
                question_row,
                config_index=config_index,
                default_correct_option_id=correct_option_id,
            )
            options = self._latex_poll_options(question_row)
        else:
            options, arrangement_hash = arrange_options_non_latex(question_row)
            correct_option_id = options.index(question_row.correct_option_text)

        return QuizQuestion(
            question_id=question_row.question_key,
            source_question_id=question_row.id,
            prompt=question_row.question_text,
            options=options,
            correct_option_id=correct_option_id,
            explanation=question_row.short_explanation,
            topic_id=question_row.topic_id,
            scaled_score=selected_question.scaled_score,
            band=selected_question.band,
            cognitive_level=selected_question.cognitive_level,
            processing_complexity=selected_question.processing_complexity,
            distractor_complexity=selected_question.distractor_complexity,
            note_reference=selected_question.note_reference,
            has_latex=question_row.has_latex,
            arrangement_hash=arrangement_hash,
            config_index=config_index,
            question_asset_url=question_asset_url,
            explanation_asset_url=self._resolve_explanation_asset_url(question_row),
            time_allocated_seconds=self._calculate_time_allocated_seconds(
                selected_question
            ),
        )

    def _calculate_time_allocated_seconds(
        self, question: AdaptiveQuestionProfile
    ) -> int:
        return calculate_question_time_limit(question)

    def _build_question_progress_text(self, session: QuizSessionState) -> str:
        return f"Question {session.current_index + 1} of {session.total_questions}"

    def _build_feedback_text(
        self,
        question: QuizQuestion,
        *,
        is_correct: bool,
        multiline: bool = False,
    ) -> str:
        if is_correct:
            if multiline:
                return "✅ Correct\nNice work."
            return "✅ Correct. Nice work."
        if multiline:
            return (
                "❌ Wrong\n"
                f"The correct answer was {self._correct_option_label(question)}."
            )
        return f"❌ Wrong. The correct answer was {self._correct_option_label(question)}."

    def _build_feedback_with_explanation_text(
        self,
        question: QuizQuestion,
        *,
        is_correct: bool,
    ) -> str:
        feedback = self._build_feedback_text(
            question,
            is_correct=is_correct,
            multiline=True,
        )
        if question.explanation:
            return f"{feedback}\n\nExplanation: {question.explanation}"
        return feedback

    async def _send_answer_actions(self, session: QuizSessionState, *, bot) -> None:
        message = await self._send_action_message(
            bot=bot,
            chat_id=session.chat_id,
            text=build_answer_action_prompt(),
            reply_markup=build_answer_action_keyboard(),
        )
        session.answer_action_message_id = getattr(message, "message_id", None)

    async def _send_action_message(self, *, bot, chat_id: int, text: str, reply_markup):
        try:
            return await bot.send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=reply_markup,
            )
        except TypeError:
            return await bot.send_message(chat_id=chat_id, text=text)

    def _build_completion_summary(self, session: QuizSessionState) -> dict:
        answered_questions = [
            question
            for question in session.questions
            if question.was_answered_correctly is not None
        ]
        answered_count = len(answered_questions)
        accuracy_percent = (
            round((session.score / answered_count) * 100) if answered_count else 0
        )
        average_time_seconds = round(
            sum(question.time_taken_seconds or 0 for question in answered_questions)
            / answered_count,
            1,
        ) if answered_count else 0.0

        topic_rows: dict[str, list[bool]] = {}
        for question in answered_questions:
            topic = question.topic_id or "General"
            topic_rows.setdefault(topic, []).append(bool(question.was_answered_correctly))

        strongest_topic = None
        weakest_topic = None
        if topic_rows:
            ranked_topics = sorted(
                (
                    (
                        round(sum(1 for value in values if value) / len(values), 4),
                        topic,
                    )
                    for topic, values in topic_rows.items()
                ),
                key=lambda item: (item[0], item[1]),
            )
            weakest_topic = self._humanize_topic_name(ranked_topics[0][1])
            strongest_topic = self._humanize_topic_name(ranked_topics[-1][1])

        if accuracy_percent >= 85:
            tier = "Excellent"
        elif accuracy_percent >= 65:
            tier = "Solid"
        else:
            tier = "Needs Review"

        recommendation = (
            f"Review {weakest_topic} before your next round."
            if weakest_topic is not None
            else "Keep building consistency with another short quiz."
        )

        longest_question = self._question_timing_summary(
            max(
                (
                    question
                    for question in answered_questions
                    if question.time_taken_seconds is not None
                ),
                key=lambda question: question.time_taken_seconds,
                default=None,
            ),
            session=session,
        )
        fastest_question = self._question_timing_summary(
            min(
                (
                    question
                    for question in answered_questions
                    if question.time_taken_seconds is not None
                ),
                key=lambda question: question.time_taken_seconds,
                default=None,
            ),
            session=session,
        )

        return {
            "course_name": session.course_name,
            "score": session.score,
            "total_questions": session.total_questions,
            "accuracy_percent": accuracy_percent,
            "tier": tier,
            "average_time_seconds": average_time_seconds,
            "strongest_topic": strongest_topic,
            "weakest_topic": weakest_topic,
            "recommendation": recommendation,
            "longest_question": longest_question,
            "fastest_question": fastest_question,
        }

    def _humanize_topic_name(self, topic: str | None) -> str | None:
        if topic is None:
            return None
        return topic.replace("-", " ").replace("_", " ").title()

    def _question_timing_summary(
        self,
        question: QuizQuestion | None,
        *,
        session: QuizSessionState,
    ) -> dict | None:
        if question is None or question.time_taken_seconds is None:
            return None
        try:
            question_number = session.questions.index(question) + 1
        except ValueError:
            question_number = None
        return {
            "question_number": question_number,
            "time_seconds": round(question.time_taken_seconds, 1),
        }

    def _correct_option_label(self, question) -> str:
        if question.has_latex:
            return self._latex_poll_options(question)[question.correct_option_id]
        return question.options[question.correct_option_id]

    def _latex_poll_options(self, question) -> list[str]:
        option_count = len(question.options)
        return [chr(65 + index) for index in range(option_count)]

    def _resolve_latex_variant(
        self,
        question_row,
        *,
        config_index: int,
        default_correct_option_id: int,
    ) -> tuple[str | None, int]:
        asset_variants = list(getattr(question_row, "asset_variants", ()) or ())
        matching_variant = next(
            (
                variant
                for variant in asset_variants
                if getattr(variant, "variant_index", None) == config_index
                and self._variant_matches_current_bot(variant)
            ),
            None,
        )
        if matching_variant is None:
            return getattr(question_row, "question_asset_url", None), default_correct_option_id

        option_order = list(getattr(matching_variant, "option_order", ()) or ())
        if default_correct_option_id in option_order:
            correct_option_id = option_order.index(default_correct_option_id)
        else:
            correct_option_id = default_correct_option_id
        return getattr(matching_variant, "question_asset_url", None), correct_option_id

    def _resolve_explanation_asset_url(self, question_row) -> str | None:
        explanation_asset_urls_by_bot = getattr(
            question_row,
            "explanation_asset_urls_by_bot",
            None,
        )
        if isinstance(explanation_asset_urls_by_bot, dict):
            bot_url = explanation_asset_urls_by_bot.get(self.bot_id)
            if bot_url:
                return bot_url
        return getattr(question_row, "explanation_asset_url", None)

    def _variant_matches_current_bot(self, variant) -> bool:
        variant_bot_id = getattr(variant, "bot_id", None)
        if variant_bot_id == self.bot_id:
            return True
        return variant_bot_id is None and self.bot_id == TANJAH_BOT_ID

    def _require_state_store(self) -> None:
        if self.state_store is None:
            raise RuntimeError("QuizSessionService requires an InteractiveStateStore.")
