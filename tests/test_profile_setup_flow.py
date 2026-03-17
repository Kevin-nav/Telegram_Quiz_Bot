from types import SimpleNamespace

import pytest

from src.bot.handlers.profile_setup import handle_profile_setup_callback


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


class FakeProfileService:
    async def update_study_profile(self, *args, **kwargs):
        return None

    async def mark_onboarding_complete(self, *args, **kwargs):
        return SimpleNamespace()


class FakeQuery:
    def __init__(self, data: str):
        self.data = data
        self.calls = []

    async def answer(self):
        return None

    async def edit_message_text(self, text, reply_markup=None):
        self.calls.append({"text": text, "reply_markup": reply_markup})


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
