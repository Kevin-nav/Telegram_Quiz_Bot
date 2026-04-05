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
        "explanation_asset_keys_by_bot",
        "explanation_asset_urls_by_bot",
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


def test_question_asset_variant_model_has_bot_id_column():
    from src.infra.db.models.question_asset_variant import QuestionAssetVariant

    columns = {column.name for column in QuestionAssetVariant.__table__.columns}

    assert "bot_id" in columns
