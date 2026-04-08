from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal


Phase = Literal["cold_start", "warm", "established"]
AttemptClassification = Literal[
    "MASTERED",
    "LEARNED",
    "DEVELOPING",
    "CARELESS_OR_MISCONCEPTION",
    "KNOWLEDGE_GAP",
    "SIGNIFICANT_GAP",
]


@dataclass(slots=True)
class AdaptiveStudentState:
    overall_skill: float = 2.5
    topic_skills: dict[str, float] = field(default_factory=dict)
    cognitive_profile: dict[str, float] = field(default_factory=dict)
    processing_profile: dict[str, float] = field(default_factory=dict)
    misconception_flags: list[dict] = field(default_factory=list)
    phase: Phase = "cold_start"
    total_quizzes_completed: int = 0
    total_attempts: int = 0
    exam_date: datetime | None = None
    last_topic_activity: dict[str, datetime] = field(default_factory=dict)


@dataclass(slots=True)
class AdaptiveQuestionProfile:
    question_id: str
    topic_id: str
    scaled_score: float
    band: int = 3
    cognitive_level: str | None = None
    processing_complexity: float | None = None
    distractor_complexity: float | None = None
    note_reference: float | None = None
    question_type: str = "MCQ"
    option_count: int = 4
    has_latex: bool = False
    arrangement_hash: str | None = None
    config_index: int | None = None


@dataclass(slots=True)
class SrsState:
    box: int = 0
    last_presented_at: datetime | None = None
    last_correct_at: datetime | None = None
    last_transition_at: datetime | None = None


@dataclass(slots=True)
class AttemptRecord:
    is_correct: bool
    arrangement_hash: str | None = None
    config_index: int | None = None


@dataclass(slots=True)
class AttemptHistorySummary:
    total_attempts: int = 0
    wrong_attempts: int = 0
    last_wrong_at: datetime | None = None
