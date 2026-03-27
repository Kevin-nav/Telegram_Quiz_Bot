from types import SimpleNamespace

import pytest

from src.bot.handlers.home import QUIZ_SELECTION_KEY, handle_home_callback
from src.domains.quiz.service import NoQuizQuestionsAvailableError


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

    def get_faculties(self):
        return [{"code": "engineering", "name": "Faculty of Engineering"}]

    def get_courses(self, faculty_code, program_code, level_code, semester_code):
        return list(self.courses)


class AsyncCatalogService:
    def __init__(self, courses=None):
        self.courses = courses or []

    async def get_faculties(self):
        return [{"code": "engineering", "name": "Faculty of Engineering"}]

    async def get_courses(self, faculty_code, program_code, level_code, semester_code):
        return list(self.courses)


class FakeQuizSessionService:
    def __init__(self, *, error: Exception | None = None):
        self.calls = []
        self.error = error

    async def start_quiz(self, **kwargs):
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return None


class FakePerformanceService:
    async def get_summary(self, user_id: int):
        return {
            "quiz_count": 3,
            "attempt_count": 18,
            "accuracy_percent": 72,
            "average_time_seconds": 14.5,
            "strongest_course": "Signals",
            "weakest_course": "Linear Electronics",
            "recommendation": "Review Linear Electronics next.",
        }


class FakeQuery:
    def __init__(self, data: str, *, message_id: int = 1):
        self.data = data
        self.calls = []
        self.answers = []
        self.cleared_reply_markup = 0
        self.message = SimpleNamespace(
            chat=SimpleNamespace(id=77),
            chat_id=77,
            message_id=message_id,
        )

    async def answer(self, text=None, show_alert=False):
        self.answers.append({"text": text, "show_alert": show_alert})

    async def edit_message_text(self, text, reply_markup=None):
        self.calls.append({"text": text, "reply_markup": reply_markup})

    async def edit_message_reply_markup(self, reply_markup=None):
        self.cleared_reply_markup += 1


def _make_user(**overrides):
    payload = {
        "id": 42,
        "preferred_course_code": "calculus",
        "faculty_code": "engineering",
        "program_code": "electrical-and-electronics-engineering",
        "level_code": "200",
        "semester_code": "first",
        "has_active_quiz": False,
    }
    payload.update(overrides)
    return SimpleNamespace(**payload)


@pytest.mark.asyncio
async def test_start_quiz_from_home_shows_profile_courses():
    user = _make_user()
    query = FakeQuery("home:start_quiz")
    context = SimpleNamespace(
        application=SimpleNamespace(
            bot_data={
                "profile_service": FakeProfileService(user),
                "catalog_service": FakeCatalogService(
                    courses=[
                        {"code": "linear-electronics", "name": "Linear Electronics"},
                        {"code": "thermodynamics", "name": "Thermodynamics"},
                    ]
                ),
            }
        ),
        user_data={},
    )
    update = SimpleNamespace(
        callback_query=query,
        effective_user=SimpleNamespace(id=42),
    )

    await handle_home_callback(update, context)

    assert "choose a course" in query.calls[-1]["text"].lower()
    callbacks = [
        row[0].callback_data for row in query.calls[-1]["reply_markup"].inline_keyboard
    ]
    assert callbacks == [
        "quiz:course:linear-electronics",
        "quiz:course:thermodynamics",
        "home:start_quiz",
    ]


@pytest.mark.asyncio
async def test_start_quiz_from_home_shows_profile_courses_with_async_catalog_service():
    user = _make_user()
    query = FakeQuery("home:start_quiz")
    context = SimpleNamespace(
        application=SimpleNamespace(
            bot_data={
                "profile_service": FakeProfileService(user),
                "catalog_service": AsyncCatalogService(
                    courses=[
                        {"code": "linear-electronics", "name": "Linear Electronics"},
                        {"code": "thermodynamics", "name": "Thermodynamics"},
                    ]
                ),
            }
        ),
        user_data={},
    )
    update = SimpleNamespace(
        callback_query=query,
        effective_user=SimpleNamespace(id=42),
    )

    await handle_home_callback(update, context)

    assert "choose a course" in query.calls[-1]["text"].lower()
    callbacks = [
        row[0].callback_data for row in query.calls[-1]["reply_markup"].inline_keyboard
    ]
    assert callbacks == [
        "quiz:course:linear-electronics",
        "quiz:course:thermodynamics",
        "home:start_quiz",
    ]


@pytest.mark.asyncio
async def test_selecting_quiz_course_prompts_for_length():
    user = _make_user()
    query = FakeQuery("quiz:course:linear-electronics")
    context = SimpleNamespace(
        application=SimpleNamespace(
            bot_data={
                "profile_service": FakeProfileService(user),
                "catalog_service": FakeCatalogService(
                    courses=[
                        {"code": "linear-electronics", "name": "Linear Electronics"},
                    ]
                ),
            }
        ),
        user_data={},
    )
    update = SimpleNamespace(
        callback_query=query,
        effective_user=SimpleNamespace(id=42),
    )

    await handle_home_callback(update, context)

    assert "how many questions" in query.calls[-1]["text"].lower()
    assert context.user_data[QUIZ_SELECTION_KEY] == {
        "course_id": "linear-electronics",
        "course_name": "Linear Electronics",
    }


@pytest.mark.asyncio
async def test_starting_selected_course_without_questions_shows_empty_message():
    user = _make_user()
    query = FakeQuery("quiz:length:10")
    quiz_session_service = FakeQuizSessionService(
        error=NoQuizQuestionsAvailableError("linear-electronics")
    )
    context = SimpleNamespace(
        application=SimpleNamespace(
            bot_data={
                "profile_service": FakeProfileService(user),
                "quiz_session_service": quiz_session_service,
            }
        ),
        user_data={
            QUIZ_SELECTION_KEY: {
                "course_id": "linear-electronics",
                "course_name": "Linear Electronics",
            }
        },
        bot=SimpleNamespace(),
    )
    update = SimpleNamespace(
        callback_query=query,
        effective_user=SimpleNamespace(id=42),
    )

    await handle_home_callback(update, context)

    assert "no questions are available" in query.calls[-1]["text"].lower()
    assert quiz_session_service.calls


@pytest.mark.asyncio
async def test_study_settings_opens_faculty_setup():
    user = _make_user()
    query = FakeQuery("home:study_settings")
    context = SimpleNamespace(
        application=SimpleNamespace(
            bot_data={
                "profile_service": FakeProfileService(user),
                "catalog_service": FakeCatalogService(),
            }
        ),
        user_data={},
    )
    update = SimpleNamespace(
        callback_query=query,
        effective_user=SimpleNamespace(id=42),
    )

    await handle_home_callback(update, context)

    assert "choose your faculty" in query.calls[-1]["text"].lower()


@pytest.mark.asyncio
async def test_stale_home_callback_is_rejected_and_keyboard_is_cleared():
    user = _make_user()
    query = FakeQuery("home:start_quiz", message_id=10)
    context = SimpleNamespace(
        application=SimpleNamespace(
            bot_data={
                "profile_service": FakeProfileService(user),
                "catalog_service": FakeCatalogService(),
            }
        ),
        user_data={"active_interactive_message_id": 99},
    )
    update = SimpleNamespace(
        callback_query=query,
        effective_user=SimpleNamespace(id=42),
    )

    await handle_home_callback(update, context)

    assert query.answers[-1]["text"] == "This menu is out of date. Use the latest message."
    assert query.cleared_reply_markup == 1
    assert not query.calls


@pytest.mark.asyncio
async def test_home_performance_renders_real_summary():
    user = _make_user()
    query = FakeQuery("home:performance")
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
        callback_query=query,
        effective_user=SimpleNamespace(id=42),
    )

    await handle_home_callback(update, context)

    assert "overall accuracy: 72%" in query.calls[-1]["text"].lower()
