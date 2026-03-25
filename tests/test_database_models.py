def test_analytics_event_model_has_expected_columns():
    from src.infra.db.models.analytics_event import AnalyticsEvent

    columns = {column.name for column in AnalyticsEvent.__table__.columns}

    assert {"id", "event_type", "user_id", "metadata", "created_at"} <= columns


def test_adaptive_runtime_models_have_expected_columns():
    from src.infra.db.models.adaptive_review_flag import AdaptiveReviewFlag
    from src.infra.db.models.student_question_srs import StudentQuestionSrs

    review_columns = {column.name for column in AdaptiveReviewFlag.__table__.columns}
    srs_columns = {column.name for column in StudentQuestionSrs.__table__.columns}

    assert {"id", "question_id", "flag_type", "reason", "status", "created_at"} <= review_columns
    assert {"id", "user_id", "course_id", "question_id", "box", "created_at"} <= srs_columns
