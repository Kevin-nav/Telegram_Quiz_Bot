from types import SimpleNamespace

import pytest

from src.bot.handlers.start import start_command
from src.infra.redis.state_store import UserProfileRecord


class FakeProfileService:
    def __init__(self, user):
        self.user = user
        self.calls = []

    async def load_or_initialize_user(
        self, telegram_user_id: int, display_name: str | None = None
    ):
        self.calls.append((telegram_user_id, display_name))
        return self.user


class FakeStateStore:
    def __init__(self, user=None):
        self.user = user
        self.saved_profiles = []
        self.claimed = []

    async def get_user_profile(self, user_id: int):
        return self.user

    async def set_user_profile(self, profile):
        self.user = profile
        self.saved_profiles.append(profile)

    async def claim_analytics_event(self, user_id: int, event_type: str, ttl_seconds: int = 0):
        self.claimed.append((user_id, event_type))
        return True


class FakeScheduler:
    def __init__(self):
        self.calls = []

    def schedule_coroutine(self, coro):
        self.calls.append(coro)
        coro.close()


class FakeMessage:
    def __init__(self):
        self.calls = []

    async def reply_text(self, text, reply_markup=None):
        self.calls.append({"text": text, "reply_markup": reply_markup})
        return SimpleNamespace(message_id=len(self.calls))


@pytest.mark.asyncio
async def test_start_routes_new_user_to_setup(monkeypatch):
    async def mock_record_analytics_event(*args, **kwargs):
        return None

    monkeypatch.setattr(
        "src.bot.handlers.start.enqueue_record_analytics_event",
        mock_record_analytics_event,
    )

    message = FakeMessage()
    user = SimpleNamespace(
        id=42,
        username="kevin",
        first_name="Kevin",
        full_name="Kevin Doe",
    )
    state_store = FakeStateStore()
    profile_service = FakeProfileService(
        UserProfileRecord(
            id=42,
            display_name="Kevin",
            onboarding_completed=False,
        )
    )
    scheduler = FakeScheduler()
    context = SimpleNamespace(
        application=SimpleNamespace(
            bot_data={
                "state_store": state_store,
                "background_scheduler": scheduler,
                "profile_service": profile_service,
            }
        ),
        user_data={},
    )
    update = SimpleNamespace(effective_user=user, message=message)

    await start_command(update, context)

    assert message.calls
    assert "set up your study profile" in message.calls[0]["text"].lower()
    assert profile_service.calls == [(42, "Kevin")]
    assert len(scheduler.calls) == 1
    assert context.user_data["active_interactive_message_id"] == 1


@pytest.mark.asyncio
async def test_start_routes_returning_user_to_home(monkeypatch):
    async def mock_record_analytics_event(*args, **kwargs):
        return None

    monkeypatch.setattr(
        "src.bot.handlers.start.enqueue_record_analytics_event",
        mock_record_analytics_event,
    )

    message = FakeMessage()
    user = SimpleNamespace(
        id=42,
        username="kevin",
        first_name="Kevin",
        full_name="Kevin Doe",
    )
    stored_user = UserProfileRecord(
        id=42,
        onboarding_completed=True,
        faculty_code="engineering",
        program_code="mechanical-engineering",
        level_code="100",
        semester_code="first",
        preferred_course_code="calculus",
        has_active_quiz=False,
    )
    profile_service = FakeProfileService(stored_user)
    scheduler = FakeScheduler()
    context = SimpleNamespace(
        application=SimpleNamespace(
            bot_data={
                "state_store": FakeStateStore(stored_user),
                "background_scheduler": scheduler,
                "profile_service": profile_service,
            }
        ),
        user_data={},
    )
    update = SimpleNamespace(effective_user=user, message=message)

    await start_command(update, context)

    assert message.calls
    assert "study home" in message.calls[0]["text"].lower()
    assert "semester: first" in message.calls[0]["text"].lower()
    assert profile_service.calls == [(42, "Kevin")]
    assert len(scheduler.calls) == 1
    assert context.user_data["active_interactive_message_id"] == 1


@pytest.mark.asyncio
async def test_start_still_replies_when_no_background_scheduler(monkeypatch):
    async def mock_record_analytics_event(*args, **kwargs):
        return None

    monkeypatch.setattr(
        "src.bot.handlers.start.enqueue_record_analytics_event",
        mock_record_analytics_event,
    )

    message = FakeMessage()
    user = SimpleNamespace(
        id=42,
        username="kevin",
        first_name="Kevin",
        full_name="Kevin Doe",
    )
    profile_service = FakeProfileService(
        UserProfileRecord(
            id=42,
            display_name="Kevin",
            onboarding_completed=False,
        )
    )
    context = SimpleNamespace(
        application=SimpleNamespace(
            bot_data={
                "state_store": FakeStateStore(),
                "profile_service": profile_service,
            }
        ),
        user_data={},
    )
    update = SimpleNamespace(effective_user=user, message=message)

    await start_command(update, context)

    assert message.calls
    assert "set up your study profile" in message.calls[0]["text"].lower()


@pytest.mark.asyncio
async def test_start_uses_profile_service_when_cache_is_empty(monkeypatch):
    async def mock_record_analytics_event(*args, **kwargs):
        return None

    monkeypatch.setattr(
        "src.bot.handlers.start.enqueue_record_analytics_event",
        mock_record_analytics_event,
    )

    message = FakeMessage()
    user = SimpleNamespace(
        id=42,
        username="kevin",
        first_name="Kevin",
        full_name="Kevin Doe",
    )
    stored_user = UserProfileRecord(
        id=42,
        onboarding_completed=True,
        faculty_code="engineering",
        program_code="mechanical-engineering",
        level_code="100",
        semester_code="first",
    )
    profile_service = FakeProfileService(stored_user)
    context = SimpleNamespace(
        application=SimpleNamespace(
            bot_data={
                "state_store": FakeStateStore(),
                "profile_service": profile_service,
            }
        ),
        user_data={},
    )
    update = SimpleNamespace(effective_user=user, message=message)

    await start_command(update, context)

    assert "study home" in message.calls[0]["text"].lower()
    assert profile_service.calls == [(42, "Kevin")]
