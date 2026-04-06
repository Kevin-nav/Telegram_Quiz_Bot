from src.domains.admin.analytics_service import AdminAnalyticsService


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
