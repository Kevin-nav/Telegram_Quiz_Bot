from __future__ import annotations

import random

from src.domains.adaptive.models import AdaptiveStudentState


def student_overall_skill(student_state: AdaptiveStudentState) -> float:
    return float(student_state.overall_skill)


def order_quiz(
    selected_questions: list,
    student_state: AdaptiveStudentState,
    *,
    rng: random.Random | None = None,
):
    if rng is None:
        rng = random.Random()

    overall_skill = student_overall_skill(student_state)
    easy = [q for q in selected_questions if q.scaled_score <= overall_skill]
    medium = [
        q
        for q in selected_questions
        if overall_skill < q.scaled_score <= overall_skill + 1.0
    ]
    hard = [q for q in selected_questions if q.scaled_score > overall_skill + 1.0]

    for bucket in (easy, medium, hard):
        rng.shuffle(bucket)

    n = len(selected_questions)
    warmup_count = max(1, round(n * 0.2))
    cooldown_count = max(1, round(n * 0.15))

    ordered = []
    ordered.extend(easy[:warmup_count])
    ordered.extend(hard)
    ordered.extend(medium)
    ordered.extend(easy[warmup_count:])

    easy_tail = [q for q in ordered if q in easy]
    cooldown = easy_tail[-cooldown_count:] if easy_tail else []
    for question in cooldown:
        if question in ordered:
            ordered.remove(question)
            ordered.append(question)

    return ordered[:n]
