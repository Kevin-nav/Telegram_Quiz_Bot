from __future__ import annotations

from src.domains.question_bank.schemas import ImportedQuestion


SUPPORTED_QUESTION_TYPES = {"MCQ", "T/F"}
SUPPORTED_COGNITIVE_LEVELS = {
    "Remembering",
    "Understanding",
    "Applying",
    "Analyzing",
    "Evaluating",
}


def validate_imported_question(question: ImportedQuestion) -> list[str]:
    errors: list[str] = []

    if not question.question_text.strip():
        errors.append("question_text must not be empty")
    if not question.short_explanation.strip():
        errors.append("short_explanation must not be empty")
    if not question.topic_id.strip():
        errors.append("topic_id must not be empty")

    if not question.options:
        errors.append("options must contain at least one option")
    elif any(not option.strip() for option in question.options):
        errors.append("options must not contain blank values")

    if question.correct_option_text not in question.options:
        errors.append("correct_option_text must match one of the options")

    if question.option_count != len(question.options):
        errors.append("option_count must match the number of options")

    if question.question_type not in SUPPORTED_QUESTION_TYPES:
        errors.append(f"question_type must be one of {sorted(SUPPORTED_QUESTION_TYPES)}")

    if question.cognitive_level not in SUPPORTED_COGNITIVE_LEVELS:
        errors.append(
            f"cognitive_level must be one of {sorted(SUPPORTED_COGNITIVE_LEVELS)}"
        )

    if not 1.0 <= question.scaled_score <= 5.0:
        errors.append("scaled_score must be between 1.0 and 5.0")

    if question.raw_score is not None and question.raw_score < 0:
        errors.append("raw_score must be greater than or equal to 0")

    if question.base_score is not None and question.base_score < 0:
        errors.append("base_score must be greater than or equal to 0")

    if not 1 <= question.band <= 5:
        errors.append("band must be between 1 and 5")

    for field_name, value in (
        ("note_reference", question.note_reference),
        ("distractor_complexity", question.distractor_complexity),
        ("processing_complexity", question.processing_complexity),
    ):
        if value < 1.0:
            errors.append(f"{field_name} must be greater than or equal to 1.0")

    # negative_stem is optional for non-MCQ types (e.g. T/F uses statement_clarity).
    # When absent it is defaulted to 0.0, so we only validate it when it was present.
    if question.negative_stem > 0.0 and question.negative_stem < 1.0:
        errors.append("negative_stem must be greater than or equal to 1.0")

    return errors


def is_valid_imported_question(question: ImportedQuestion) -> bool:
    return not validate_imported_question(question)
