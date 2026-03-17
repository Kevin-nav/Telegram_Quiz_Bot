def test_user_model_has_study_profile_columns():
    from src.infra.db.models.user import User

    columns = {column.name for column in User.__table__.columns}

    assert {
        "faculty_code",
        "program_code",
        "level_code",
        "semester_code",
        "preferred_course_code",
        "onboarding_completed",
    } <= columns
