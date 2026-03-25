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


def test_staff_access_models_have_expected_columns():
    from src.infra.db.models.audit_log import AuditLog
    from src.infra.db.models.permission import Permission
    from src.infra.db.models.staff_role import StaffRole
    from src.infra.db.models.staff_role_permission import StaffRolePermission
    from src.infra.db.models.staff_user import StaffUser
    from src.infra.db.models.staff_user_permission import StaffUserPermission
    from src.infra.db.models.staff_user_role import StaffUserRole

    staff_user_columns = {column.name for column in StaffUser.__table__.columns}
    staff_role_columns = {column.name for column in StaffRole.__table__.columns}
    permission_columns = {column.name for column in Permission.__table__.columns}
    staff_user_role_columns = {column.name for column in StaffUserRole.__table__.columns}
    staff_user_permission_columns = {
        column.name for column in StaffUserPermission.__table__.columns
    }
    staff_role_permission_columns = {
        column.name for column in StaffRolePermission.__table__.columns
    }
    audit_log_columns = {column.name for column in AuditLog.__table__.columns}

    assert {"id", "email", "is_active"} <= staff_user_columns
    assert {"id", "code", "name", "created_at"} <= staff_role_columns
    assert {"id", "code", "name", "created_at"} <= permission_columns
    assert {"id", "staff_user_id", "staff_role_id"} <= staff_user_role_columns
    assert {"id", "staff_user_id", "permission_id"} <= staff_user_permission_columns
    assert {"id", "staff_role_id", "permission_id"} <= staff_role_permission_columns
    assert {"id", "actor_staff_user_id", "action", "entity_type", "entity_id", "created_at"} <= audit_log_columns


def test_catalog_models_have_expected_columns():
    from src.infra.db.models.catalog_course import CatalogCourse
    from src.infra.db.models.catalog_faculty import CatalogFaculty
    from src.infra.db.models.catalog_level import CatalogLevel
    from src.infra.db.models.catalog_program import CatalogProgram
    from src.infra.db.models.catalog_semester import CatalogSemester
    from src.infra.db.models.program_course_offering import ProgramCourseOffering

    faculty_columns = {column.name for column in CatalogFaculty.__table__.columns}
    program_columns = {column.name for column in CatalogProgram.__table__.columns}
    level_columns = {column.name for column in CatalogLevel.__table__.columns}
    semester_columns = {column.name for column in CatalogSemester.__table__.columns}
    course_columns = {column.name for column in CatalogCourse.__table__.columns}
    offering_columns = {column.name for column in ProgramCourseOffering.__table__.columns}

    assert {"id", "code", "name", "is_active", "created_at", "updated_at"} <= faculty_columns
    assert {"id", "faculty_code", "code", "name", "is_active", "created_at", "updated_at"} <= program_columns
    assert {"id", "code", "name", "is_active", "created_at", "updated_at"} <= level_columns
    assert {"id", "code", "name", "is_active", "created_at", "updated_at"} <= semester_columns
    assert {"id", "code", "name", "short_name", "description", "is_active", "created_at", "updated_at"} <= course_columns
    assert {
        "id",
        "program_code",
        "level_code",
        "semester_code",
        "course_code",
        "is_active",
        "created_at",
        "updated_at",
    } <= offering_columns
