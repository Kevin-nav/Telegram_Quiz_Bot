from types import SimpleNamespace

import pytest

from src.bot.handlers.commands import performance_command, quiz_command
from src.domains.quiz.models import QuizQuestion, QuizSessionState
from src.domains.quiz.service import QuizSessionService
from src.infra.redis.state_store import InteractiveStateStore
from tests.fakes import FakeRedis


class FakeProfileService:
    def __init__(self, user):
        self.user = user

    async def load_or_initialize_user(
        self, telegram_user_id: int, display_name: str | None = None
    ):
        return self.user


class FakeCatalogService:
    def __init__(self, courses=None):
        self.courses = courses or []

    async def get_courses(self, faculty_code, program_code, level_code, semester_code):
        return list(self.courses)


class FakeMessage:
    def __init__(self):
        self.calls = []

    async def reply_text(self, text, reply_markup=None):
        self.calls.append({"text": text, "reply_markup": reply_markup})
        return SimpleNamespace(message_id=len(self.calls))


class FakePerformanceService:
    async def get_summary(self, user_id: int):
        return {
            "quiz_count": 5,
            "attempt_count": 40,
            "accuracy_percent": 70,
            "average_time_seconds": 16.2,
            "strongest_course": "Signals",
            "weakest_course": "Thermodynamics",
            "recommendation": "Review Thermodynamics next.",
        }


@pytest.mark.asyncio
async def test_quiz_command_shows_course_picker_and_updates_active_message():
    user = SimpleNamespace(
        id=42,
        faculty_code="engineering",
        program_code="electrical-and-electronics-engineering",
        level_code="200",
        semester_code="first",
        has_active_quiz=False,
    )
    message = FakeMessage()
    context = SimpleNamespace(
        application=SimpleNamespace(
            bot_data={
                "profile_service": FakeProfileService(user),
                "catalog_service": FakeCatalogService(
                    courses=[
                        {"code": "linear-electronics", "name": "Linear Electronics"},
                        {"code": "signals", "name": "Signals"},
                    ]
                ),
            }
        ),
        user_data={},
    )
    update = SimpleNamespace(
        effective_user=SimpleNamespace(id=42),
        message=message,
    )

    await quiz_command(update, context)

    assert "choose a course" in message.calls[0]["text"].lower()
    callbacks = [
        row[0].callback_data for row in message.calls[0]["reply_markup"].inline_keyboard
    ]
    assert callbacks == [
        "quiz:course:linear-electronics",
        "quiz:course:signals",
        "home:start_quiz",
    ]
    assert context.user_data["active_interactive_message_id"] == 1


@pytest.mark.asyncio
async def test_quiz_command_shows_no_available_courses_message_when_filtered_empty():
    user = SimpleNamespace(
        id=42,
        faculty_code="engineering",
        program_code="electrical-and-electronics-engineering",
        level_code="200",
        semester_code="first",
        has_active_quiz=False,
    )
    message = FakeMessage()
    context = SimpleNamespace(
        application=SimpleNamespace(
            bot_data={
                "profile_service": FakeProfileService(user),
                "catalog_service": FakeCatalogService(courses=[]),
            }
        ),
        user_data={},
    )
    update = SimpleNamespace(
        effective_user=SimpleNamespace(id=42),
        message=message,
    )

    await quiz_command(update, context)

    assert "no courses with questions are available" in message.calls[0]["text"].lower()


@pytest.mark.asyncio
async def test_quiz_command_invalidates_active_quiz_report_buttons():
    store = InteractiveStateStore(FakeRedis())
    session = QuizSessionState(
        session_id="session-1",
        user_id=42,
        chat_id=77,
        course_id="linear-electronics",
        course_name="Linear Electronics",
        questions=[
            QuizQuestion(
                question_id="q1",
                prompt="Question 1",
                options=["A", "B"],
                correct_option_id=1,
            )
        ],
        question_action_message_id=201,
        answer_action_message_id=202,
    )
    await store.set_quiz_session(session)
    await store.set_active_quiz(42, "session-1")

    user = SimpleNamespace(
        id=42,
        faculty_code="engineering",
        program_code="electrical-and-electronics-engineering",
        level_code="200",
        semester_code="first",
        has_active_quiz=True,
    )
    message = FakeMessage()
    context = SimpleNamespace(
        application=SimpleNamespace(
            bot_data={
                "profile_service": FakeProfileService(user),
                "catalog_service": FakeCatalogService(
                    courses=[
                        {"code": "linear-electronics", "name": "Linear Electronics"},
                    ]
                ),
                "quiz_session_service": QuizSessionService(state_store=store),
            }
        ),
        user_data={},
    )
    update = SimpleNamespace(
        effective_user=SimpleNamespace(id=42),
        message=message,
    )

    await quiz_command(update, context)

    updated_session = await store.get_quiz_session("session-1")
    assert updated_session is not None
    assert updated_session.question_action_message_id is None
    assert updated_session.answer_action_message_id is None


@pytest.mark.asyncio
async def test_performance_command_hides_performance_button_in_keyboard():
    user = SimpleNamespace(
        id=42,
        faculty_code="engineering",
        program_code="electrical-and-electronics-engineering",
        level_code="200",
        semester_code="first",
        has_active_quiz=False,
    )
    message = FakeMessage()
    context = SimpleNamespace(
        application=SimpleNamespace(
            bot_data={
                "profile_service": FakeProfileService(user),
                "performance_service": FakePerformanceService(),
            }
        ),
        user_data={},
    )
    update = SimpleNamespace(
        effective_user=SimpleNamespace(id=42),
        message=message,
    )

    await performance_command(update, context)

    callbacks = [
        row[0].callback_data for row in message.calls[0]["reply_markup"].inline_keyboard
    ]
    assert "home:performance" not in callbacks
