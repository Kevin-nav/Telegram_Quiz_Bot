from __future__ import annotations

import random
from typing import Sequence

from src.domains.adaptive.models import AttemptRecord


def choose_latex_config_index(
    option_count: int,
    previous_config_indices: Sequence[int] | None = None,
    *,
    rng: random.Random | None = None,
) -> int:
    if option_count <= 0:
        raise ValueError("option_count must be positive")

    if rng is None:
        rng = random.Random()

    previous_config_indices = list(previous_config_indices or [])
    available = set(range(option_count)) - set(previous_config_indices)

    if not available:
        available = set(range(option_count))
        if previous_config_indices:
            available.discard(previous_config_indices[-1])

    if not available:
        available = set(range(option_count))

    return rng.choice(sorted(available))


def arrange_options_non_latex(
    question,
    *,
    rng: random.Random | None = None,
):
    if rng is None:
        rng = random.Random()

    original_options = list(question.options)
    indexed_options = list(enumerate(original_options))
    rng.shuffle(indexed_options)

    arranged_options = [option for _, option in indexed_options]
    arrangement_hash = "-".join(chr(65 + original_index) for original_index, _ in indexed_options)
    return arranged_options, arrangement_hash


def arrange_options_latex(
    question,
    previous_config_indices: Sequence[int] | None = None,
    *,
    rng: random.Random | None = None,
):
    config_index = choose_latex_config_index(
        question.option_count,
        previous_config_indices,
        rng=rng,
    )
    return config_index


def detect_position_memorization(attempts: Sequence[AttemptRecord]) -> bool:
    if len(attempts) < 2:
        return False

    correct_arrangements = {attempt.arrangement_hash for attempt in attempts if attempt.is_correct}
    wrong_arrangements = {attempt.arrangement_hash for attempt in attempts if not attempt.is_correct}

    return bool(correct_arrangements and wrong_arrangements)
