import pytest

from src.domains.quiz.models import PollMapRecord, QuizQuestion, QuizSessionState
from src.infra.redis.state_store import InteractiveStateStore, UserProfileRecord
from tests.fakes import FakeRedis


@pytest.mark.asyncio
async def test_user_profile_round_trip_tracks_active_quiz():
    store = InteractiveStateStore(FakeRedis())

    await store.set_user_profile(
        UserProfileRecord(
            id=42,
            display_name="Kevin",
            preferred_course_code="calculus",
            onboarding_completed=True,
        )
    )
    await store.set_active_quiz(42, "session-1")

    profile = await store.get_user_profile(42)

    assert profile is not None
    assert profile.display_name == "Kevin"
    assert profile.has_active_quiz is True


@pytest.mark.asyncio
async def test_quiz_state_and_poll_map_round_trip():
    store = InteractiveStateStore(FakeRedis())
    session = QuizSessionState(
        session_id="session-1",
        user_id=42,
        chat_id=99,
        course_id="calculus",
        course_name="Calculus",
        questions=[
            QuizQuestion(
                question_id="q1",
                prompt="Question 1",
                options=["A", "B", "C", "D"],
                correct_option_id=1,
            )
        ],
    )
    await store.set_quiz_session(session)
    await store.set_poll_map(
        PollMapRecord(
            poll_id="poll-1",
            session_id="session-1",
            question_id="q1",
            question_index=0,
            user_id=42,
        )
    )

    loaded_session = await store.get_quiz_session("session-1")
    poll_map = await store.get_poll_map("poll-1")

    assert loaded_session is not None
    assert loaded_session.course_name == "Calculus"
    assert loaded_session.current_question().question_id == "q1"
    assert poll_map is not None
    assert poll_map.session_id == "session-1"


@pytest.mark.asyncio
async def test_quiz_lock_rejects_duplicate_acquire():
    store = InteractiveStateStore(FakeRedis())

    token = await store.acquire_quiz_lock("session-1")
    duplicate = await store.acquire_quiz_lock("session-1")

    assert token is not None
    assert duplicate is None

    await store.release_quiz_lock("session-1", token)
    assert await store.acquire_quiz_lock("session-1") is not None


@pytest.mark.asyncio
async def test_analytics_claim_deduplicates_same_event():
    store = InteractiveStateStore(FakeRedis())

    assert await store.claim_analytics_event(42, "User Registered") is True
    assert await store.claim_analytics_event(42, "User Registered") is False


@pytest.mark.asyncio
async def test_adaptive_snapshot_round_trip_and_invalidation():
    store = InteractiveStateStore(FakeRedis())

    await store.set_adaptive_snapshot(42, "calculus", {"overall_skill": 2.7})
    loaded = await store.get_adaptive_snapshot(42, "calculus")
    await store.invalidate_adaptive_snapshot(42, "calculus")
    cleared = await store.get_adaptive_snapshot(42, "calculus")

    assert loaded == {"overall_skill": 2.7}
    assert cleared is None


@pytest.mark.asyncio
async def test_adaptive_update_lock_rejects_duplicate_acquire():
    store = InteractiveStateStore(FakeRedis())

    token = await store.acquire_adaptive_update_lock(42, "calculus")
    duplicate = await store.acquire_adaptive_update_lock(42, "calculus")

    assert token is not None
    assert duplicate is None

    await store.release_adaptive_update_lock(42, "calculus", token)
    assert await store.acquire_adaptive_update_lock(42, "calculus") is not None


@pytest.mark.asyncio
async def test_catalog_cache_helpers_round_trip_and_invalidation():
    store = InteractiveStateStore(FakeRedis())

    faculties = [{"code": "engineering", "name": "Faculty of Engineering"}]
    programs = [{"code": "electrical-and-electronics-engineering", "name": "Electrical and Electronics Engineering"}]

    await store.cache_catalog_faculties(faculties)
    await store.cache_catalog_programs("engineering", programs)

    assert await store.get_catalog_faculties() == faculties
    assert await store.get_catalog_programs("engineering") == programs

    await store.invalidate_catalog_faculties()
    await store.invalidate_catalog_programs("engineering")

    assert await store.get_catalog_faculties() is None
    assert await store.get_catalog_programs("engineering") is None


@pytest.mark.asyncio
async def test_catalog_cache_bulk_invalidation_clears_all_tracked_keys():
    store = InteractiveStateStore(FakeRedis())

    await store.cache_catalog_faculties([{"code": "engineering", "name": "Faculty of Engineering"}])
    await store.cache_catalog_programs(
        "engineering",
        [{"code": "electrical-and-electronics-engineering", "name": "Electrical and Electronics Engineering"}],
    )

    await store.invalidate_catalog_cache()

    assert await store.get_catalog_faculties() is None
    assert await store.get_catalog_programs("engineering") is None
