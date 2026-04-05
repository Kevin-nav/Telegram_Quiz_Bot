from types import SimpleNamespace

import pytest

from src.bot.handlers.profile_setup import handle_profile_setup_callback
from src.bot.runtime_config import DEFAULT_BOT_THEMES, BotRuntimeConfig


class FakeCatalogService:
    def get_faculties(self):
        return [{"code": "engineering", "name": "Faculty of Engineering"}]

    def get_programs(self, faculty_code: str):
        assert faculty_code == "engineering"
        return [{"code": "mechanical-engineering", "name": "Mechanical Engineering"}]

    def get_levels(self, program_code: str):
        return [{"code": "100", "name": "Level 100"}]

    def get_semesters(self, program_code: str, level_code: str):
        return [{"code": "first", "name": "First Semester"}]

    def get_courses(self, faculty_code: str, program_code: str, level_code: str, semester_code: str):
        return [{"code": "calculus", "name": "Calculus"}]


class AsyncCatalogService:
    async def get_faculties(self):
        return [{"code": "engineering", "name": "Faculty of Engineering"}]

    async def get_programs(self, faculty_code: str):
        assert faculty_code == "engineering"
        return [{"code": "mechanical-engineering", "name": "Mechanical Engineering"}]

    async def get_levels(self, program_code: str):
        return [{"code": "100", "name": "Level 100"}]

    async def get_semesters(self, program_code: str, level_code: str):
        return [{"code": "first", "name": "First Semester"}]

    async def get_courses(self, faculty_code: str, program_code: str, level_code: str, semester_code: str):
        return [{"code": "calculus", "name": "Calculus"}]


class FakeProfileService:
    def __init__(self):
        self.persist_calls = []

    async def persist_profile_record(self, payload: dict):
        self.persist_calls.append(payload)
        return SimpleNamespace(
            id=payload["user_id"],
            display_name=payload.get("display_name"),
            faculty_code=payload.get("faculty_code"),
            program_code=payload.get("program_code"),
            level_code=payload.get("level_code"),
            semester_code=payload.get("semester_code"),
            preferred_course_code=payload.get("preferred_course_code"),
            onboarding_completed=payload.get("onboarding_completed", False),
        )


class FakeStateStore:
    def __init__(self):
        self.saved_profiles = []

    async def set_user_profile(self, profile):
        self.saved_profiles.append(profile)


class FakeQuery:
    def __init__(self, data: str):
        self.data = data
        self.calls = []
        self.answers = []
        self.cleared_reply_markup = 0
        self.message = SimpleNamespace(message_id=1)

    async def answer(self, text=None, show_alert=False):
        self.answers.append({"text": text, "show_alert": show_alert})

    async def edit_message_text(self, text, reply_markup=None):
        self.calls.append({"text": text, "reply_markup": reply_markup})

    async def edit_message_reply_markup(self, reply_markup=None):
        self.cleared_reply_markup += 1


@pytest.mark.asyncio
async def test_profile_setup_advances_from_faculty_to_program():
    query = FakeQuery("profile:start:setup")
    context = SimpleNamespace(
        application=SimpleNamespace(
            bot_data={
                "catalog_service": FakeCatalogService(),
                "profile_service": FakeProfileService(),
            }
        ),
        user_data={},
    )
    update = SimpleNamespace(
        callback_query=query,
        effective_user=SimpleNamespace(id=42),
    )

    await handle_profile_setup_callback(update, context)

    assert "Choose your faculty" in query.calls[-1]["text"]

    query.data = "profile:faculty:engineering"
    await handle_profile_setup_callback(update, context)

    assert "Choose your program" in query.calls[-1]["text"]


@pytest.mark.asyncio
async def test_profile_setup_completion_sets_first_semester_in_cached_profile():
    query = FakeQuery("profile:start:setup")
    state_store = FakeStateStore()
    profile_service = FakeProfileService()
    context = SimpleNamespace(
        application=SimpleNamespace(
            bot_data={
                "catalog_service": FakeCatalogService(),
                "profile_service": profile_service,
                "state_store": state_store,
            }
        ),
        user_data={},
    )
    update = SimpleNamespace(
        callback_query=query,
        effective_user=SimpleNamespace(id=42, first_name="Kevin", full_name="Kevin Doe"),
    )

    await handle_profile_setup_callback(update, context)
    query.data = "profile:faculty:engineering"
    await handle_profile_setup_callback(update, context)
    query.data = "profile:program:mechanical-engineering"
    await handle_profile_setup_callback(update, context)
    query.data = "profile:level:100"
    await handle_profile_setup_callback(update, context)

    assert state_store.saved_profiles[-1].semester_code == "first"
    assert profile_service.persist_calls[-1]["onboarding_completed"] is True
    assert "First Semester" in query.calls[-1]["text"]


@pytest.mark.asyncio
async def test_profile_setup_advances_with_async_catalog_service():
    query = FakeQuery("profile:start:setup")
    context = SimpleNamespace(
        application=SimpleNamespace(
            bot_data={
                "catalog_service": AsyncCatalogService(),
                "profile_service": FakeProfileService(),
            }
        ),
        user_data={},
    )
    update = SimpleNamespace(
        callback_query=query,
        effective_user=SimpleNamespace(id=42, first_name="Kevin", full_name="Kevin Doe"),
    )

    await handle_profile_setup_callback(update, context)

    assert "Choose your faculty" in query.calls[-1]["text"]

    query.data = "profile:faculty:engineering"
    await handle_profile_setup_callback(update, context)

    assert "Choose your program" in query.calls[-1]["text"]


@pytest.mark.asyncio
async def test_profile_setup_shows_catalog_unavailable_when_no_faculties_exist():
    class EmptyCatalogService:
        async def get_faculties(self):
            return []

    query = FakeQuery("profile:start:setup")
    context = SimpleNamespace(
        application=SimpleNamespace(
            bot_data={
                "catalog_service": EmptyCatalogService(),
                "profile_service": FakeProfileService(),
            }
        ),
        user_data={},
    )
    update = SimpleNamespace(
        callback_query=query,
        effective_user=SimpleNamespace(id=42, first_name="Kevin", full_name="Kevin Doe"),
    )

    await handle_profile_setup_callback(update, context)

    assert "catalog is unavailable" in query.calls[-1]["text"].lower()


@pytest.mark.asyncio
async def test_adarkwa_profile_setup_starts_at_program_and_persists_fixed_engineering_defaults():
    query = FakeQuery("profile:start:setup")
    state_store = FakeStateStore()
    profile_service = FakeProfileService()
    context = SimpleNamespace(
        application=SimpleNamespace(
            bot_data={
                "bot_config": BotRuntimeConfig(
                    bot_id="adarkwa",
                    telegram_bot_token="adarkwa-token",
                    webhook_secret="adarkwa-secret",
                    webhook_path="/webhook/adarkwa",
                    allowed_course_codes=(),
                    theme=DEFAULT_BOT_THEMES["adarkwa"],
                    profile_setup_start_step="program",
                    fixed_faculty_code="engineering",
                    fixed_faculty_name="Faculty Of Engineering",
                    fixed_level_code="100",
                    fixed_level_name="Level 100",
                ),
                "catalog_service": FakeCatalogService(),
                "profile_service": profile_service,
                "state_store": state_store,
            }
        ),
        user_data={},
    )
    update = SimpleNamespace(
        callback_query=query,
        effective_user=SimpleNamespace(id=42, first_name="Kevin", full_name="Kevin Doe"),
    )

    await handle_profile_setup_callback(update, context)

    assert "Choose your program" in query.calls[-1]["text"]
    assert "Faculty: Faculty Of Engineering" in query.calls[-1]["text"]
    assert "Level: Level 100" in query.calls[-1]["text"]
    assert query.calls[-1]["reply_markup"].inline_keyboard[-1][0].text == "Cancel"

    query.data = "profile:program:mechanical-engineering"
    await handle_profile_setup_callback(update, context)

    assert profile_service.persist_calls[-1]["faculty_code"] == "engineering"
    assert profile_service.persist_calls[-1]["program_code"] == "mechanical-engineering"
    assert profile_service.persist_calls[-1]["level_code"] == "100"
    assert profile_service.persist_calls[-1]["semester_code"] == "first"
