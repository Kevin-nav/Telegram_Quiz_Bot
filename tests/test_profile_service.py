import pytest

from src.domains.profile.service import ProfileService
from src.infra.redis.state_store import InteractiveStateStore
from tests.fakes import FakeRedis


class FakeSession:
    def __init__(self):
        self.users = {}
        self.user_bot_profiles = {}
        self._next_profile_id = 1

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, model, key):
        if model.__name__ == "User":
            return self.users.get(key)
        return None

    def add(self, record):
        if record.__class__.__name__ == "User":
            self.users[record.id] = record
            return
        if record.__class__.__name__ == "UserBotProfile":
            if getattr(record, "id", None) is None:
                record.id = self._next_profile_id
                self._next_profile_id += 1
            self.user_bot_profiles[(record.user_id, record.bot_id)] = record
            return

    async def commit(self):
        return None

    async def refresh(self, user):
        return None

    async def flush(self):
        return None

    async def execute(self, statement):
        model = statement.column_descriptions[0]["entity"]
        if model.__name__ != "UserBotProfile":
            raise AssertionError(f"Unexpected model query: {model}")

        criteria = {}
        for criterion in statement._where_criteria:
            criteria[criterion.left.name] = criterion.right.value
        record = self.user_bot_profiles.get((criteria["user_id"], criteria["bot_id"]))
        return FakeScalarResult(record)


class FakeScalarResult:
    def __init__(self, record):
        self.record = record

    def scalar_one_or_none(self):
        return self.record


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


@pytest.mark.asyncio
async def test_profile_service_keeps_bot_profiles_separate():
    session_factory = FakeSessionFactory()
    tanjah_service = ProfileService(
        session_factory=session_factory,
        state_store=InteractiveStateStore(FakeRedis(), bot_id="tanjah"),
        bot_id="tanjah",
    )
    adarkwa_service = ProfileService(
        session_factory=session_factory,
        state_store=InteractiveStateStore(FakeRedis(), bot_id="adarkwa"),
        bot_id="adarkwa",
    )

    await adarkwa_service.persist_profile_record(
        {
            "user_id": 42,
            "display_name": "Kevin",
            "faculty_code": "engineering",
            "program_code": "mechanical-engineering",
            "level_code": "100",
            "semester_code": "first",
            "onboarding_completed": True,
        }
    )
    tanjah_user = await tanjah_service.load_or_initialize_user(42, display_name="Kevin")
    adarkwa_user = await adarkwa_service.load_or_initialize_user(42, display_name="Kevin")

    assert tanjah_user.display_name == "Kevin"
    assert tanjah_user.faculty_code is None
    assert tanjah_user.onboarding_completed is False
    assert adarkwa_user.faculty_code == "engineering"
    assert adarkwa_user.level_code == "100"
    assert adarkwa_user.onboarding_completed is True
