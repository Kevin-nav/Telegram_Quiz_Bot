from datetime import UTC, datetime

from src.domains.quiz.models import QuizQuestion


def test_quiz_question_supports_runtime_arrangement_metadata():
    question = QuizQuestion(
        question_id="q1",
        source_question_id=17,
        prompt="Q",
        options=["A", "B", "C", "D"],
        correct_option_id=0,
        explanation="E",
        arrangement_hash="A-B-C-D",
        config_index=2,
        question_asset_url="https://cdn.example.com/q1.png",
        explanation_asset_url="https://cdn.example.com/q1-explanation.png",
        has_latex=True,
        topic_id="algebra",
        scaled_score=3.2,
        band=3,
        cognitive_level="Analyzing",
        processing_complexity=1.5,
        distractor_complexity=1.2,
        note_reference=1.4,
        time_allocated_seconds=90,
        presented_at=datetime(2026, 3, 25, 12, 0, tzinfo=UTC),
    )

    payload = question.to_dict()
    restored = QuizQuestion.from_dict(payload)

    assert restored.arrangement_hash == "A-B-C-D"
    assert restored.source_question_id == 17
    assert restored.config_index == 2
    assert restored.question_asset_url == "https://cdn.example.com/q1.png"
    assert restored.explanation_asset_url == "https://cdn.example.com/q1-explanation.png"
    assert restored.has_latex is True
    assert restored.topic_id == "algebra"
    assert restored.scaled_score == 3.2
    assert restored.band == 3
    assert restored.cognitive_level == "Analyzing"
    assert restored.processing_complexity == 1.5
    assert restored.distractor_complexity == 1.2
    assert restored.note_reference == 1.4
    assert restored.time_allocated_seconds == 90
    assert restored.presented_at == datetime(2026, 3, 25, 12, 0, tzinfo=UTC)
