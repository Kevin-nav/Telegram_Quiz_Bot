from src.domains.quiz.models import QuizQuestion


def test_quiz_question_supports_runtime_arrangement_metadata():
    question = QuizQuestion(
        question_id="q1",
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
    )

    payload = question.to_dict()
    restored = QuizQuestion.from_dict(payload)

    assert restored.arrangement_hash == "A-B-C-D"
    assert restored.config_index == 2
    assert restored.question_asset_url == "https://cdn.example.com/q1.png"
    assert restored.explanation_asset_url == "https://cdn.example.com/q1-explanation.png"
    assert restored.has_latex is True
    assert restored.topic_id == "algebra"
