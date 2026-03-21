def test_question_bank_model_has_expected_algorithm_columns():
    from src.infra.db.models.question_bank import QuestionBank

    columns = {column.name for column in QuestionBank.__table__.columns}

    assert {
        "question_key",
        "course_id",
        "question_text",
        "options",
        "correct_option_text",
        "short_explanation",
        "scaled_score",
        "band",
        "topic_id",
        "cognitive_level",
        "processing_complexity",
        "distractor_complexity",
        "note_reference",
        "has_latex",
        "status",
    } <= columns


def test_question_bank_related_models_are_registered():
    from src.infra.db.models import (
        QuestionAssetVariant,
        QuestionAttempt,
        QuestionBank,
        StudentCourseState,
    )

    assert QuestionBank.__tablename__ == "question_bank"
    assert QuestionAssetVariant.__tablename__ == "question_asset_variants"
    assert QuestionAttempt.__tablename__ == "question_attempts"
    assert StudentCourseState.__tablename__ == "student_course_state"
