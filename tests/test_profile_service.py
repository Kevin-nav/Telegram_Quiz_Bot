import pytest

from src.domains.profile.service import ProfileService


class FakeSession:
    def __init__(self):
        self.users = {}

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, model, key):
        return self.users.get(key)

    def add(self, user):
        self.users[user.id] = user

    async def commit(self):
        return None

    async def refresh(self, user):
        return None


class FakeSessionFactory:
    def __init__(self):
        self.session = FakeSession()

    def __call__(self):
        return self.session


@pytest.mark.asyncio
async def test_profile_service_marks_onboarding_complete():
    session_factory = FakeSessionFactory()
    service = ProfileService(session_factory=session_factory)

    user = await service.load_or_initialize_user(telegram_user_id=42, display_name="Kevin")
    assert user.display_name == "Kevin"
    assert user.onboarding_completed is False

    user = await service.update_study_profile(
        42,
        faculty_code="engineering",
        program_code="mechanical-engineering",
        level_code="100",
        semester_code="first",
        preferred_course_code="calculus",
    )
    assert user.faculty_code == "engineering"
    assert user.program_code == "mechanical-engineering"
    assert user.semester_code == "first"

    user = await service.mark_onboarding_complete(42)
    assert user.onboarding_completed is True


@pytest.mark.asyncio
async def test_profile_service_persist_profile_record_upserts_fields():
    session_factory = FakeSessionFactory()
    service = ProfileService(session_factory=session_factory)

    user = await service.persist_profile_record(
        {
            "user_id": 7,
            "display_name": "Kevin",
            "faculty_code": "engineering",
            "program_code": "mechanical-engineering",
            "level_code": "100",
            "onboarding_completed": True,
        }
    )

    assert user.id == 7
    assert user.display_name == "Kevin"
    assert user.faculty_code == "engineering"
    assert user.onboarding_completed is True
