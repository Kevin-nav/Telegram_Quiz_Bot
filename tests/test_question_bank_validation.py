from src.domains.question_bank import (
    ImportedQuestion,
    build_question_key,
    build_question_source_checksum,
    is_valid_imported_question,
    validate_imported_question,
)


def make_question(**overrides) -> ImportedQuestion:
    payload = {
        "question_text": "What is Ohm's law?",
        "options": ["V = IR", "P = IV", "Q = CV", "F = ma"],
        "correct_option_text": "V = IR",
        "short_explanation": "Ohm's law states that voltage equals current times resistance.",
        "raw_score": 1.8,
        "scaled_score": 1.5,
        "band": 1,
        "has_latex": False,
        "base_score": 1.2,
        "note_reference": 1.0,
        "distractor_complexity": 1.1,
        "processing_complexity": 1.0,
        "negative_stem": 1.0,
        "cognitive_level": "Understanding",
        "option_count": 4,
        "topic_id": "circuit_basics",
        "question_type": "MCQ",
    }
    payload.update(overrides)
    return ImportedQuestion(**payload)


def test_validation_rejects_correct_option_not_in_options():
    question = make_question(correct_option_text="Not an option")

    errors = validate_imported_question(question)

    assert "correct_option_text must match one of the options" in errors


def test_validation_rejects_option_count_mismatch():
    question = make_question(option_count=3)

    errors = validate_imported_question(question)

    assert "option_count must match the number of options" in errors


def test_validation_accepts_valid_import_question_and_builds_stable_identifiers():
    question = make_question()

    assert validate_imported_question(question) == []
    assert is_valid_imported_question(question) is True
    assert build_question_key("linear-electronics", question) == build_question_key(
        "linear-electronics", question
    )
    assert build_question_source_checksum(question) == build_question_source_checksum(
        question
    )
