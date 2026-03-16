def test_analytics_event_model_has_expected_columns():
    from src.infra.db.models.analytics_event import AnalyticsEvent

    columns = {column.name for column in AnalyticsEvent.__table__.columns}

    assert {"id", "event_type", "user_id", "metadata", "created_at"} <= columns
