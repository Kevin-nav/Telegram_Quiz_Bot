import pytest

from src.domains.admin.analytics_service import AdminAnalyticsService


class FakeCacheStore:
    def __init__(self):
        self.values = {}

    async def get_json(self, namespace, **_kwargs):
        return self.values.get(namespace)

    async def set_json(self, namespace, payload, **_kwargs):
        self.values[namespace] = payload


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
