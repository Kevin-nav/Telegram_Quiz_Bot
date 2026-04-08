from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.domains.admin.analytics_service import AdminAnalyticsService


class FakeCacheStore:
    def __init__(self):
        self.values = {}
        self.dirty = set()
        self.refresh_claims = set()

    async def get_json(self, namespace, **_kwargs):
        return self.values.get(namespace)

    async def set_json(self, namespace, payload, **_kwargs):
        self.values[namespace] = payload
        self.dirty.discard(namespace)
        self.refresh_claims.discard(namespace)

    async def is_dirty(self, namespace, **_kwargs):
        return namespace in self.dirty

    async def mark_dirty(self, namespace, **_kwargs):
        self.dirty.add(namespace)

    async def claim_refresh(self, namespace, **_kwargs):
        if namespace in self.refresh_claims:
            return False
        self.refresh_claims.add(namespace)
        return True

    async def clear_dirty(self, namespace, **_kwargs):
        self.dirty.discard(namespace)

    async def complete_refresh(self, namespace, **_kwargs):
        self.refresh_claims.discard(namespace)


def test_serialize_misconception_flags_normalizes_raw_adaptive_flags():
    service = AdminAnalyticsService(cache_store=object())

    payload = service._serialize_misconception_flags(
        [
            {
                "topic_id": "integrating_factor",
                "selected_distractor": "Option C",
                "times_selected": 3,
                "resolved": False,
            },
            {
                "topic": "entropy",
                "description": "Conflates entropy change of system vs surroundings.",
                "severity": "medium",
            },
        ]
    )

    assert payload == [
        {
            "topic": "integrating_factor",
            "description": "Repeatedly selects 'Option C' on related questions.",
            "severity": "high",
        },
        {
            "topic": "entropy",
            "description": "Conflates entropy change of system vs surroundings.",
            "severity": "medium",
        },
    ]


def test_serialize_misconception_flags_skips_empty_entries():
    service = AdminAnalyticsService(cache_store=object())

    payload = service._serialize_misconception_flags(
        [{}, {"question_id": None}, "invalid-entry"]  # type: ignore[list-item]
    )

    assert payload == []


class StubAnalyticsService(AdminAnalyticsService):
    async def get_summary(self, *, active_bot_id=None, course_codes=None):
        return {
            "kpis": [
                {
                    "label": "Active Users (7d)",
                    "value": "12",
                    "change": "+20.0%",
                    "trend": "up",
                }
            ],
            "leaderboard": [{"rank": 1, "telegram_username": "top_user"}],
        }

    async def _count_staff_users(self, *, active_only: bool) -> int:
        return 3 if active_only else 5

    async def _count_questions(self, *, active_bot_id, course_codes, status=None) -> int:
        return 2 if status == "needs_review" else 40

    async def _count_question_reports(self, *, active_bot_id, course_codes, status):
        return 7 if status == "open" else 9

    async def _list_recent_reports(self, *, active_bot_id, course_codes, limit: int):
        return [
            {
                "id": 1,
                "question_id": 11,
                "question_key": "CALC_001",
                "question_text": "Question",
                "course_name": "Calculus",
                "student_username": "student_one",
                "student_reasoning": "Please review.",
                "status": "open",
                "created_at": "2026-04-08T00:00:00+00:00",
            }
        ][:limit]


@pytest.mark.asyncio
async def test_dashboard_summary_aggregates_counts_and_recent_items():
    service = StubAnalyticsService(cache_store=FakeCacheStore())

    payload = await service.get_dashboard_summary(
        active_bot_id="adarkwa",
        course_codes={"calculus"},
    )

    assert payload["staff_count"] == 5
    assert payload["active_staff_count"] == 3
    assert payload["question_count"] == 40
    assert payload["review_question_count"] == 2
    assert payload["open_reports_count"] == 7
    assert payload["recent_reports"][0]["question_key"] == "CALC_001"


class StaleSummaryService(AdminAnalyticsService):
    async def precompute_summary(self, **_kwargs):
        raise AssertionError("stale summary should not recompute synchronously")


@pytest.mark.asyncio
async def test_summary_returns_stale_payload_and_triggers_background_refresh(monkeypatch):
    cache_store = FakeCacheStore()
    await cache_store.set_json(
        "analytics-summary",
        {"kpis": [{"label": "Cached"}]},
        bot_id="adarkwa",
        ttl_seconds=60,
    )
    await cache_store.mark_dirty("analytics-summary", bot_id="adarkwa")
    enqueue_refresh = AsyncMock()
    monkeypatch.setattr(
        "src.domains.admin.analytics_service.enqueue_precompute_admin_analytics",
        enqueue_refresh,
    )
    service = StaleSummaryService(cache_store=cache_store)

    payload = await service.get_summary(active_bot_id="adarkwa", course_codes={"signals"})

    assert payload == {"kpis": [{"label": "Cached"}]}
    enqueue_refresh.assert_awaited_once_with(
        {"bot_id": "adarkwa", "course_codes": ["signals"]}
    )


class DenormalizedStudentAnalyticsService(AdminAnalyticsService):
    async def _get_user(self, user_id: int):
        return SimpleNamespace(
            id=user_id,
            display_name="Student One",
            created_at=datetime(2026, 4, 1, tzinfo=timezone.utc),
            last_active_at=datetime(2026, 4, 8, tzinfo=timezone.utc),
            current_streak=4,
            longest_streak=7,
        )

    async def _get_user_profile(self, user_id: int, active_bot_id=None):
        return SimpleNamespace(
            faculty_code="eng",
            program_code="eee",
            level_code="300",
            semester_code="first",
            preferred_course_code="signals",
            onboarding_completed=True,
            created_at=datetime(2026, 4, 1, tzinfo=timezone.utc),
        )

    async def _list_attempts(self, **_kwargs):
        return [
            SimpleNamespace(
                id=1,
                course_id="signals",
                question_key="SIG_001",
                is_correct=False,
                time_taken_seconds=20.0,
                created_at=datetime(2026, 4, 8, tzinfo=timezone.utc),
            )
        ]

    async def _list_student_course_states(self, **_kwargs):
        return [
            SimpleNamespace(
                course_id="signals",
                overall_skill=3.2,
                phase="warm",
                topic_skills={"fourier": 3.0},
                cognitive_profile={},
                processing_profile={},
                misconception_flags=[],
                total_quizzes_completed=2,
                total_attempts=5,
                total_correct=3,
                avg_time_per_question=11.5,
                exam_date=None,
            )
        ]

    async def _list_session_summaries(self, **_kwargs):
        return [
            SimpleNamespace(
                total_questions=5,
                correct_count=3,
                avg_time_seconds=11.5,
                completed_at=datetime(2026, 4, 7, tzinfo=timezone.utc),
            )
        ]

    async def _list_question_reports(self, **_kwargs):
        return []

    async def _get_telegram_identity(self, user_id: int):
        return SimpleNamespace(telegram_user_id=user_id, username="student_one")

    async def _load_course_names(self, course_ids):
        return {course_id: "Signals" for course_id in course_ids}

    async def _load_faculty_name(self, _faculty_code):
        return "Engineering"

    async def _load_program_name(self, _program_code):
        return "Electrical Engineering"

    async def _find_leaderboard_entry(self, **_kwargs):
        return None

    async def _build_srs_distribution(self, **_kwargs):
        return []


@pytest.mark.asyncio
async def test_student_detail_prefers_denormalized_metrics_and_session_summaries():
    service = DenormalizedStudentAnalyticsService(cache_store=FakeCacheStore())

    payload = await service.get_student_detail(42, active_bot_id="adarkwa")

    assert payload is not None
    assert payload["profile"]["total_questions_answered"] == 5
    assert payload["profile"]["total_correct"] == 3
    assert payload["profile"]["current_streak"] == 4
    assert payload["courses"][0]["total_attempts"] == 5
    assert payload["courses"][0]["avg_time_per_question"] == 11.5
    assert payload["weekly_progress"][-1]["attempts"] == 5
