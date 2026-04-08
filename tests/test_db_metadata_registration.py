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
    assert "user_bot_profiles" in table_names


def test_hot_path_indexes_are_registered():
    from src.infra.db.models.program_course_offering import ProgramCourseOffering
    from src.infra.db.models.question_attempt import QuestionAttempt
    from src.infra.db.models.question_bank import QuestionBank
    from src.infra.db.models.question_report import QuestionReport

    question_bank_indexes = {index.name for index in QuestionBank.__table__.indexes}
    question_attempt_indexes = {index.name for index in QuestionAttempt.__table__.indexes}
    question_report_indexes = {index.name for index in QuestionReport.__table__.indexes}
    offering_indexes = {index.name for index in ProgramCourseOffering.__table__.indexes}

    assert "ix_question_bank_course_status_id" in question_bank_indexes
    assert "ix_question_attempts_bot_user_created_at" in question_attempt_indexes
    assert "ix_question_attempts_bot_user_question_created_at" in question_attempt_indexes
    assert "ix_question_reports_bot_status_created_at" in question_report_indexes
    assert "ix_pco_program_level_semester_active_course" in offering_indexes
