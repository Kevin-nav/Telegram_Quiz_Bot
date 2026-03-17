from types import SimpleNamespace

import pytest

from src.bot.handlers.start import start_command


class FakeProfileService:
    def __init__(self, user):
        self.user = user

    async def load_or_initialize_user(self, telegram_user_id: int, display_name: str | None = None):
        self.user.display_name = display_name
        return self.user


class FakeMessage:
    def __init__(self):
        self.calls = []

    async def reply_text(self, text, reply_markup=None):
        self.calls.append({"text": text, "reply_markup": reply_markup})


@pytest.mark.asyncio
async def test_start_routes_new_user_to_setup(monkeypatch):
    async def mock_track_event(*args, **kwargs):
        return None

    monkeypatch.setattr("src.bot.handlers.start.analytics.track_event", mock_track_event)

    message = FakeMessage()
    user = SimpleNamespace(
        id=42,
        username="kevin",
        first_name="Kevin",
        full_name="Kevin Doe",
    )
    stored_user = SimpleNamespace(id=42, onboarding_completed=False)
    context = SimpleNamespace(
        application=SimpleNamespace(
            bot_data={
                "profile_service": FakeProfileService(stored_user),
            }
        )
    )
    update = SimpleNamespace(effective_user=user, message=message)

    await start_command(update, context)

    assert message.calls
    assert "set up your study profile" in message.calls[0]["text"].lower()


@pytest.mark.asyncio
async def test_start_routes_returning_user_to_home(monkeypatch):
    async def mock_track_event(*args, **kwargs):
        return None

    monkeypatch.setattr("src.bot.handlers.start.analytics.track_event", mock_track_event)

    message = FakeMessage()
    user = SimpleNamespace(
        id=42,
        username="kevin",
        first_name="Kevin",
        full_name="Kevin Doe",
    )
    stored_user = SimpleNamespace(
        id=42,
        onboarding_completed=True,
        faculty_code="engineering",
        program_code="mechanical-engineering",
        level_code="100",
        semester_code="first",
        preferred_course_code="calculus",
        has_active_quiz=False,
    )
    context = SimpleNamespace(
        application=SimpleNamespace(
            bot_data={
                "profile_service": FakeProfileService(stored_user),
            }
        )
    )
    update = SimpleNamespace(effective_user=user, message=message)

    await start_command(update, context)

    assert message.calls
    assert "study home" in message.calls[0]["text"].lower()
