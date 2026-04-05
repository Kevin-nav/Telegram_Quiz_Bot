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
        question_action_message_id=301,
        answer_action_message_id=302,
        last_answered_question_id="q0",
        last_answered_question_index=0,
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
    assert loaded_session.question_action_message_id == 301
    assert loaded_session.answer_action_message_id == 302
    assert loaded_session.last_answered_question_id == "q0"
    assert loaded_session.last_answered_question_index == 0
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


@pytest.mark.asyncio
async def test_report_draft_round_trip_and_clear():
    store = InteractiveStateStore(FakeRedis())
    draft = {
        "user_id": 42,
        "session_id": "session-1",
        "question_key": "q1",
        "question_index": 0,
        "report_scope": "question",
        "report_reason": "question_unclear",
    }

    await store.set_report_draft(42, draft)
    loaded = await store.get_report_draft(42)
    await store.clear_report_draft(42)
    cleared = await store.get_report_draft(42)

    assert loaded == draft
    assert cleared is None


@pytest.mark.asyncio
async def test_report_note_state_round_trip_and_clear():
    store = InteractiveStateStore(FakeRedis())
    payload = {
        "user_id": 42,
        "session_id": "session-1",
        "question_key": "q1",
        "report_scope": "answer",
        "report_reason": "explanation_is_wrong",
    }

    await store.set_pending_report_note(42, payload)
    loaded = await store.get_pending_report_note(42)
    await store.clear_pending_report_note(42)
    cleared = await store.get_pending_report_note(42)

    assert loaded == payload
    assert cleared is None


@pytest.mark.asyncio
async def test_runtime_state_is_bot_scoped_but_profile_cache_is_shared():
    redis = FakeRedis()
    tanjah_store = InteractiveStateStore(redis, bot_id="tanjah")
    adarkwa_store = InteractiveStateStore(redis, bot_id="adarkwa")

    await tanjah_store.set_user_profile(
        UserProfileRecord(
            id=42,
            display_name="Kevin",
            preferred_course_code="linear-algebra",
            onboarding_completed=True,
        )
    )
    await tanjah_store.set_active_quiz(42, "tanjah-session")
    await adarkwa_store.set_active_quiz(42, "adarkwa-session")
    await tanjah_store.set_report_draft(42, {"bot_id": "tanjah"})
    await adarkwa_store.set_report_draft(42, {"bot_id": "adarkwa"})

    tanjah_profile = await tanjah_store.get_user_profile(42)
    adarkwa_profile = await adarkwa_store.get_user_profile(42)

    assert tanjah_profile is not None
    assert adarkwa_profile is not None
    assert tanjah_profile.display_name == "Kevin"
    assert adarkwa_profile.display_name == "Kevin"
    assert await tanjah_store.get_active_quiz(42) == "tanjah-session"
    assert await adarkwa_store.get_active_quiz(42) == "adarkwa-session"
    assert await tanjah_store.get_report_draft(42) == {"bot_id": "tanjah"}
    assert await adarkwa_store.get_report_draft(42) == {"bot_id": "adarkwa"}


@pytest.mark.asyncio
async def test_adaptive_runtime_helpers_are_bot_scoped():
    redis = FakeRedis()
    tanjah_store = InteractiveStateStore(redis, bot_id="tanjah")
    adarkwa_store = InteractiveStateStore(redis, bot_id="adarkwa")

    await tanjah_store.set_adaptive_snapshot(42, "calculus", {"overall_skill": 2.7})
    await adarkwa_store.set_adaptive_snapshot(42, "calculus", {"overall_skill": 4.1})

    tanjah_lock = await tanjah_store.acquire_adaptive_update_lock(42, "calculus")
    adarkwa_lock = await adarkwa_store.acquire_adaptive_update_lock(42, "calculus")

    assert await tanjah_store.get_adaptive_snapshot(42, "calculus") == {"overall_skill": 2.7}
    assert await adarkwa_store.get_adaptive_snapshot(42, "calculus") == {"overall_skill": 4.1}
    assert tanjah_lock is not None
    assert adarkwa_lock is not None


@pytest.mark.asyncio
async def test_analytics_claim_is_bot_scoped():
    redis = FakeRedis()
    tanjah_store = InteractiveStateStore(redis, bot_id="tanjah")
    adarkwa_store = InteractiveStateStore(redis, bot_id="adarkwa")

    assert await tanjah_store.claim_analytics_event(42, "User Registered") is True
    assert await tanjah_store.claim_analytics_event(42, "User Registered") is False
    assert await adarkwa_store.claim_analytics_event(42, "User Registered") is True
    assert await adarkwa_store.claim_analytics_event(42, "User Registered") is False


@pytest.mark.asyncio
async def test_poll_maps_are_bot_scoped():
    redis = FakeRedis()
    tanjah_store = InteractiveStateStore(redis, bot_id="tanjah")
    adarkwa_store = InteractiveStateStore(redis, bot_id="adarkwa")

    await tanjah_store.set_poll_map(
        PollMapRecord(
            poll_id="shared-poll",
            session_id="tanjah-session",
            question_id="q1",
            question_index=0,
            user_id=42,
        )
    )
    await adarkwa_store.set_poll_map(
        PollMapRecord(
            poll_id="shared-poll",
            session_id="adarkwa-session",
            question_id="q2",
            question_index=0,
            user_id=42,
        )
    )

    tanjah_poll_map = await tanjah_store.get_poll_map("shared-poll")
    adarkwa_poll_map = await adarkwa_store.get_poll_map("shared-poll")

    assert tanjah_poll_map is not None
    assert adarkwa_poll_map is not None
    assert tanjah_poll_map.session_id == "tanjah-session"
    assert adarkwa_poll_map.session_id == "adarkwa-session"
