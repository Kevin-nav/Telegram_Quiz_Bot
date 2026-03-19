from types import SimpleNamespace

import pytest
from src.bot.handlers.home import handle_home_callback


class FakeProfileService:
    def __init__(self, user):
        self.user = user

    async def load_or_initialize_user(
        self, telegram_user_id: int, display_name: str | None = None
    ):
        return self.user


class FakeCatalogService:
    def get_faculties(self):
        return [{"code": "engineering", "name": "Faculty of Engineering"}]


class FakeQuery:
    def __init__(self, data: str):
        self.data = data
        self.calls = []

    async def answer(self):
        return None

    async def edit_message_text(self, text, reply_markup=None):
        self.calls.append({"text": text, "reply_markup": reply_markup})


@pytest.mark.asyncio
async def test_start_quiz_from_home_prompts_for_length():
    user = SimpleNamespace(
        id=42,
        preferred_course_code="calculus",
        has_active_quiz=False,
    )
    query = FakeQuery("home:start_quiz")
    context = SimpleNamespace(
        application=SimpleNamespace(
            bot_data={
                "profile_service": FakeProfileService(user),
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
    callbacks = [
        row[0].callback_data for row in query.calls[-1]["reply_markup"].inline_keyboard
    ]
    assert callbacks == ["quiz:length:10", "quiz:length:20", "quiz:length:30"]


@pytest.mark.asyncio
async def test_study_settings_opens_faculty_setup():
    user = SimpleNamespace(
        id=42,
        preferred_course_code="calculus",
        has_active_quiz=False,
    )
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
