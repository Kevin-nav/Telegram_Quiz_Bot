from __future__ import annotations

SRS_INTERVALS = [0, 1, 3, 7, 14, 30, 60]


def srs_interval_for_box(box: int) -> int:
    if box < 0:
        box = 0
    if box >= len(SRS_INTERVALS):
        box = len(SRS_INTERVALS) - 1
    return SRS_INTERVALS[box]


def is_srs_due(box: int, days_since_last_correct: int) -> bool:
    return days_since_last_correct >= srs_interval_for_box(box)


def advance_srs_box(current_box: int, is_correct: bool) -> int:
    if not is_correct:
        return 0
    return min(current_box + 1, len(SRS_INTERVALS) - 1)


def apply_overdue_demote(current_box: int, days_since_last_correct: int) -> int:
    interval = srs_interval_for_box(current_box)
    if interval <= 0:
        return current_box
    if days_since_last_correct > interval * 2:
        return max(0, current_box - 1)
    return current_box
