from types import SimpleNamespace
from datetime import UTC, datetime, timedelta

import pytest

from src.domains.adaptive.models import AdaptiveQuestionProfile, AdaptiveStudentState
from src.domains.adaptive.service import AdaptiveSelectionOutput
from src.domains.quiz.service import NoQuizQuestionsAvailableError, QuizSessionService
from src.infra.redis.state_store import InteractiveStateStore
from tests.fakes import FakeRedis


class FakeBot:
    def __init__(self):
        self.poll_calls = []
        self.message_calls = []
        self.photo_calls = []
        self.events = []
        self.message_id_seq = 1

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
        self.events.append(("poll", poll_id))
        return SimpleNamespace(poll=SimpleNamespace(id=poll_id))

    async def send_message(self, *, chat_id, text, reply_markup=None):
        message_id = self.message_id_seq
        self.message_id_seq += 1
        self.message_calls.append(
            {
                "chat_id": chat_id,
                "text": text,
                "reply_markup": reply_markup,
                "message_id": message_id,
            }
        )
        self.events.append(("message", text))
        return SimpleNamespace(message_id=message_id)

    async def send_photo(self, *, chat_id, photo):
        self.photo_calls.append({"chat_id": chat_id, "photo": photo})
        self.events.append(("photo", photo))


class FakeScheduler:
    def __init__(self):
        self.jobs = []

    def __call__(self, coro):
        self.jobs.append(coro)
        close = getattr(coro, "close", None)
        if close is not None:
            close()


class FakeAdaptiveLearningService:
    def __init__(self, question_rows=None):
        self.question_rows = question_rows or []
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


class FakeScheduledJob:
    def __init__(self, payload):
        self.payload = payload
        self.closed = False

    def close(self):
        self.closed = True


@pytest.mark.asyncio
async def test_start_quiz_creates_state_and_sends_first_poll():
    store = InteractiveStateStore(FakeRedis())
    adaptive_service = FakeAdaptiveLearningService(
        question_rows=[
            SimpleNamespace(
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
            SimpleNamespace(
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

    active_session = await store.get_active_quiz(42)
    loaded_session = await store.get_quiz_session(session.session_id)

    assert active_session == session.session_id
    assert loaded_session is not None
    assert loaded_session.current_poll_id == "poll-1"
    assert loaded_session.question_action_message_id is not None
    assert loaded_session.questions[0].presented_at is not None
    assert loaded_session.questions[0].time_allocated_seconds is not None
    assert loaded_session.questions[0].scaled_score == 2.0
    assert adaptive_service.calls[0]["course_id"] == "calculus"
    assert bot.poll_calls
    assert bot.message_calls[-1]["text"] == "Need to flag this question?"
    assert not bot.photo_calls
    assert bot.message_calls[0]["text"] == "Question 1 of 2"
    assert bot.poll_calls[0]["question"] == "What is the derivative of x^2?"


@pytest.mark.asyncio
async def test_poll_answer_advances_quiz_without_db_dependency(monkeypatch):
    store = InteractiveStateStore(FakeRedis())
    adaptive_service = FakeAdaptiveLearningService(
        question_rows=[
            SimpleNamespace(
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
            SimpleNamespace(
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
    first_question = session.questions[0]
    loaded_session = await store.get_quiz_session(session.session_id)
    loaded_session.questions[0].presented_at = datetime.now(UTC) - timedelta(seconds=20)
    await store.set_quiz_session(loaded_session)

    attempt_jobs: list[FakeScheduledJob] = []

    def fake_enqueue_persist_quiz_attempt(payload):
        job = FakeScheduledJob(payload)
        attempt_jobs.append(job)
        return job

    import src.domains.quiz.service as quiz_service_module

    monkeypatch.setattr(
        quiz_service_module,
        "enqueue_persist_quiz_attempt",
        fake_enqueue_persist_quiz_attempt,
    )

    handled = await service.handle_poll_answer(
        bot=bot,
        poll_answer=SimpleNamespace(
            poll_id="poll-1",
            option_ids=[first_question.correct_option_id],
        ),
        schedule_background=scheduler,
    )

    loaded_session = await store.get_quiz_session(session.session_id)

    assert handled is True
    assert loaded_session is not None
    assert loaded_session.current_index == 1
    assert loaded_session.current_poll_id == "poll-2"
    assert loaded_session.last_answered_question_id == first_question.question_id
    assert len(bot.poll_calls) == 2
    assert bot.message_calls[2]["text"].startswith("✅ Correct")
    assert "Explanation:" in bot.message_calls[2]["text"]
    assert bot.message_calls[3]["text"] == "Not correct? Report this answer if the key or explanation is off."
    assert bot.message_calls[4]["text"] == "Question 2 of 2"
    assert attempt_jobs
    assert attempt_jobs[0].payload["time_taken_seconds"] is not None
    assert attempt_jobs[0].payload["time_allocated_seconds"] is not None
    assert attempt_jobs[0].payload["metadata"]["scaled_score"] == 2.0
    assert attempt_jobs[0].payload["metadata"]["presented_at"] is not None


@pytest.mark.asyncio
async def test_select_questions_uses_adaptive_service_and_canonical_rows():
    store = InteractiveStateStore(FakeRedis())
    adaptive_service = FakeAdaptiveLearningService(
        question_rows=[
            SimpleNamespace(
                id=17,
                question_key="linear-electronics-q1",
                question_text="An ideal op-amp is characterised by",
                options=["A", "B", "C", "D"],
                correct_option_text="B",
                short_explanation="Ideal op-amps have infinite gain and input resistance.",
                topic_id="op_amp_basics",
                scaled_score=1.7,
                band=1,
                cognitive_level="Understanding",
                processing_complexity=1.0,
                distractor_complexity=1.1,
                note_reference=1.0,
                question_type="MCQ",
                option_count=4,
                has_latex=False,
                explanation_asset_url=None,
                question_asset_url="https://cdn.example.com/linear-electronics-q1.png",
            ),
        ]
    )
    service = QuizSessionService(
        state_store=store,
        adaptive_learning_service=adaptive_service,
    )

    questions = await service._select_questions(
        user_id=42,
        course_id="linear-electronics",
        course_name="Linear Electronics",
        question_count=1,
    )

    assert adaptive_service.calls[0]["course_id"] == "linear-electronics"
    assert questions[0].question_id == "linear-electronics-q1"
    assert questions[0].source_question_id == 17
    assert questions[0].options[questions[0].correct_option_id] == "B"
    assert questions[0].topic_id == "op_amp_basics"
    assert questions[0].has_latex is False
    assert questions[0].time_allocated_seconds is not None


@pytest.mark.asyncio
async def test_select_questions_raises_when_no_canonical_questions_exist():
    store = InteractiveStateStore(FakeRedis())
    adaptive_service = FakeAdaptiveLearningService(question_rows=[])
    service = QuizSessionService(
        state_store=store,
        adaptive_learning_service=adaptive_service,
    )

    with pytest.raises(NoQuizQuestionsAvailableError):
        await service._select_questions(
            user_id=42,
            course_id="linear-electronics",
            course_name="Linear Electronics",
            question_count=1,
        )


@pytest.mark.asyncio
async def test_latex_question_sends_progress_image_and_letter_poll_then_feedback():
    store = InteractiveStateStore(FakeRedis())
    adaptive_service = FakeAdaptiveLearningService(
        question_rows=[
            SimpleNamespace(
                id=17,
                question_key="linear-electronics-q1",
                question_text="Rendered from image",
                options=["Option 1", "Option 2", "Option 3", "Option 4"],
                correct_option_text="Option 2",
                short_explanation="Review the op-amp rule.",
                topic_id="op_amp_basics",
                scaled_score=1.7,
                band=1,
                cognitive_level="Understanding",
                processing_complexity=1.0,
                distractor_complexity=1.1,
                note_reference=1.0,
                question_type="MCQ",
                option_count=4,
                has_latex=True,
                explanation_asset_url="https://cdn.example.com/linear-electronics-q1-expl.png",
                question_asset_url="https://cdn.example.com/linear-electronics-q1.png",
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
        course_id="linear-electronics",
        course_name="Linear Electronics",
        question_count=1,
        schedule_background=scheduler,
    )

    assert bot.message_calls[0]["text"] == "Question 1 of 1"
    assert bot.photo_calls[0]["photo"] == "https://cdn.example.com/linear-electronics-q1.png"
    assert bot.poll_calls[0]["question"] == "Choose the correct option."
    assert bot.poll_calls[0]["options"] == ["A", "B", "C", "D"]
    assert bot.message_calls[1]["text"] == "Need to flag this question?"

    handled = await service.handle_poll_answer(
        bot=bot,
        poll_answer=SimpleNamespace(
            poll_id="poll-1",
            option_ids=[session.questions[0].correct_option_id],
        ),
        schedule_background=scheduler,
    )

    assert handled is True
    assert bot.message_calls[2]["text"] == "✅ Correct. Nice work."
    assert bot.photo_calls[1]["photo"] == "https://cdn.example.com/linear-electronics-q1-expl.png"
    assert "Quiz complete for Linear Electronics." in bot.message_calls[-1]["text"]
    assert "Accuracy:" in bot.message_calls[-1]["text"]


@pytest.mark.asyncio
async def test_latex_question_uses_selected_asset_variant_and_adjusts_correct_option():
    store = InteractiveStateStore(FakeRedis())
    adaptive_service = FakeAdaptiveLearningService(
        question_rows=[
            SimpleNamespace(
                id=17,
                question_key="logic-q1",
                question_text="Rendered from image",
                options=["True", "False"],
                correct_option_text="True",
                short_explanation="Review the statement.",
                topic_id="truth-values",
                scaled_score=1.2,
                band=1,
                cognitive_level="Understanding",
                processing_complexity=1.0,
                distractor_complexity=1.1,
                note_reference=1.0,
                question_type="T/F",
                option_count=2,
                has_latex=True,
                explanation_asset_url="https://cdn.example.com/logic-q1-expl.png",
                asset_variants=[
                    SimpleNamespace(
                        variant_index=0,
                        option_order=[0, 1],
                        question_asset_url="https://cdn.example.com/logic-q1-v0.png",
                    ),
                    SimpleNamespace(
                        variant_index=1,
                        option_order=[1, 0],
                        question_asset_url="https://cdn.example.com/logic-q1-v1.png",
                    ),
                ],
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
        course_id="logic",
        course_name="Logic",
        question_count=1,
        schedule_background=scheduler,
    )

    assert session.questions[0].question_asset_url in {
        "https://cdn.example.com/logic-q1-v0.png",
        "https://cdn.example.com/logic-q1-v1.png",
    }
    if session.questions[0].config_index == 1:
        assert session.questions[0].correct_option_id == 1
        assert bot.photo_calls[0]["photo"] == "https://cdn.example.com/logic-q1-v1.png"
    else:
        assert session.questions[0].correct_option_id == 0
        assert bot.photo_calls[0]["photo"] == "https://cdn.example.com/logic-q1-v0.png"


@pytest.mark.asyncio
async def test_poll_answer_non_latex_flow_sends_feedback_then_text_explanation():
    store = InteractiveStateStore(FakeRedis())
    adaptive_service = FakeAdaptiveLearningService(
        question_rows=[
            SimpleNamespace(
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
                explanation_asset_url=None,
                question_asset_url="https://cdn.example.com/calculus-q1.png",
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
        question_count=1,
        schedule_background=scheduler,
    )

    loaded_session = await store.get_quiz_session(session.session_id)
    loaded_session.questions[0].presented_at = datetime.now(UTC) - timedelta(seconds=8)
    await store.set_quiz_session(loaded_session)

    await service.handle_poll_answer(
        bot=bot,
        poll_answer=SimpleNamespace(
            poll_id="poll-1",
            option_ids=[1],
        ),
        schedule_background=scheduler,
    )

    assert bot.message_calls[-3]["text"].startswith(("✅ Correct\n", "❌ Wrong\n"))
    assert "apply the power rule" in bot.message_calls[-3]["text"].lower()
    assert "not correct? report this answer" in bot.message_calls[-2]["text"].lower()
    assert "Quiz complete for Calculus." in bot.message_calls[-1]["text"]
