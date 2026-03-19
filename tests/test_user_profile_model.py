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


def test_user_model_defaults_onboarding_to_false():
    from src.infra.db.models.user import User

    column = User.__table__.c.onboarding_completed

    assert column.nullable is False
    assert column.default is not None
    assert column.server_default is not None
