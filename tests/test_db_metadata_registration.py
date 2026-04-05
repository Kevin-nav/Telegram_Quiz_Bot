def test_canonical_database_import_registers_question_bank_tables():
    from src.database import Base

    table_names = set(Base.metadata.tables)

    assert "question_bank" in table_names
    assert "question_asset_variants" in table_names
    assert "student_course_state" in table_names
    assert "question_attempts" in table_names
    assert "question_reports" in table_names
    assert "student_question_srs" in table_names
    assert "analytics_events" in table_names
    assert "adaptive_review_flags" in table_names
    assert "staff_users" in table_names
    assert "staff_roles" in table_names
    assert "permissions" in table_names
    assert "staff_user_roles" in table_names
    assert "staff_user_permissions" in table_names
    assert "staff_role_permissions" in table_names
    assert "staff_bot_access" in table_names
    assert "staff_catalog_access" in table_names
    assert "audit_logs" in table_names
