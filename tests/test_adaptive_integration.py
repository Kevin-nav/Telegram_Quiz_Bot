from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.domains.adaptive.models import AdaptiveQuestionProfile, AdaptiveStudentState
from src.domains.adaptive.service import AdaptiveSelectionOutput
from src.domains.quiz.service import QuizSessionService
from src.infra.redis.state_store import InteractiveStateStore
from tests.fakes import FakeRedis


class FakeBot:
    def __init__(self):
        self.poll_calls = []

    async def send_poll(
        self,
        *,
        chat_id,
        question,
        options,
        type,
        is_anonymous,
        correct_option_id,
    ):
        poll_id = f"poll-{len(self.poll_calls) + 1}"
        self.poll_calls.append(
            {
                "chat_id": chat_id,
                "question": question,
                "options": options,
                "type": type,
                "is_anonymous": is_anonymous,
                "correct_option_id": correct_option_id,
                "poll_id": poll_id,
            }
        )
        return SimpleNamespace(poll=SimpleNamespace(id=poll_id))

    async def send_message(self, *, chat_id, text):
        return None


class FakeScheduler:
    def __init__(self):
        self.jobs = []

    def __call__(self, coro):
        self.jobs.append(coro)
        close = getattr(coro, "close", None)
        if close is not None:
            close()


class FakeQuestionBankQuestion:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class FakeAdaptiveService:
    def __init__(self, question_rows):
        self.question_rows = question_rows
        self.calls = []

    async def select_questions(self, *, user_id, course_id, quiz_length, **kwargs):
        self.calls.append(
            {
                "user_id": user_id,
                "course_id": course_id,
                "quiz_length": quiz_length,
                "kwargs": kwargs,
            }
        )
        selected_questions = [
            AdaptiveQuestionProfile(
                question_id=row.question_key,
                topic_id=row.topic_id,
                scaled_score=row.scaled_score,
                band=row.band,
                cognitive_level=row.cognitive_level,
                processing_complexity=row.processing_complexity,
                distractor_complexity=row.distractor_complexity,
                note_reference=row.note_reference,
                question_type=row.question_type,
                option_count=row.option_count,
                has_latex=row.has_latex,
            )
            for row in self.question_rows[:quiz_length]
        ]
        return AdaptiveSelectionOutput(
            student_state=AdaptiveStudentState(total_quizzes_completed=4),
            selected_questions=selected_questions,
            question_rows=list(self.question_rows),
        )


@pytest.mark.asyncio
async def test_start_quiz_uses_adaptive_selection_and_embeds_runtime_metadata():
    store = InteractiveStateStore(FakeRedis())
    adaptive_service = FakeAdaptiveService(
        [
            FakeQuestionBankQuestion(
                id=17,
                question_key="calculus-q1",
                question_text="What is the derivative of x^2?",
                options=["x", "2x", "x^2", "2"],
                correct_option_text="2x",
                short_explanation="Apply the power rule.",
                topic_id="derivatives",
                scaled_score=2.0,
                band=2,
                cognitive_level="Applying",
                processing_complexity=1.0,
                distractor_complexity=1.2,
                note_reference=1.0,
                question_type="MCQ",
                option_count=4,
                has_latex=False,
                explanation_asset_url="https://cdn.example.com/calculus-q1-expl.png",
                question_asset_url="https://cdn.example.com/calculus-q1.png",
            ),
            FakeQuestionBankQuestion(
                id=18,
                question_key="calculus-q2",
                question_text="What is the integral of 2x?",
                options=["x", "x^2", "2x", "x/2"],
                correct_option_text="x^2",
                short_explanation="Integrate term by term.",
                topic_id="integrals",
                scaled_score=2.2,
                band=2,
                cognitive_level="Applying",
                processing_complexity=1.0,
                distractor_complexity=1.1,
                note_reference=1.0,
                question_type="MCQ",
                option_count=4,
                has_latex=False,
                explanation_asset_url="https://cdn.example.com/calculus-q2-expl.png",
                question_asset_url="https://cdn.example.com/calculus-q2.png",
            ),
        ]
    )
    service = QuizSessionService(
        state_store=store,
        adaptive_learning_service=adaptive_service,
    )
    bot = FakeBot()
    scheduler = FakeScheduler()

    session = await service.start_quiz(
        bot=bot,
        user_id=42,
        chat_id=99,
        course_id="calculus",
        course_name="Calculus",
        question_count=2,
        schedule_background=scheduler,
    )

    loaded_session = await store.get_quiz_session(session.session_id)

    assert adaptive_service.calls[0]["course_id"] == "calculus"
    assert loaded_session is not None
    assert loaded_session.questions[0].presented_at is not None
    assert loaded_session.questions[0].time_allocated_seconds is not None
    assert loaded_session.questions[0].arrangement_hash is not None
    assert loaded_session.questions[0].options[loaded_session.questions[0].correct_option_id] == "2x"

