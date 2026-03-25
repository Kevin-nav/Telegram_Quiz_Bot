from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass


def _slugify(value: str, *, default: str = "item") -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.strip().lower())
    normalized = normalized.strip("-")
    return normalized or default


@dataclass(slots=True)
class ImportedQuestion:
    question_text: str
    options: list[str]
    correct_option_text: str
    short_explanation: str
    raw_score: float | None
    scaled_score: float
    band: int
    has_latex: bool
    base_score: float | None
    note_reference: float
    distractor_complexity: float
    processing_complexity: float
    negative_stem: float
    cognitive_level: str
    option_count: int
    topic_id: str
    question_type: str

    @classmethod
    def from_dict(cls, payload: dict) -> "ImportedQuestion":
        return cls(
            question_text=str(payload["question_text"]),
            options=[str(option) for option in payload["options"]],
            correct_option_text=str(payload["correct_option_text"]),
            short_explanation=str(payload["short_explanation"]),
            raw_score=(
                float(payload["raw_score"])
                if payload.get("raw_score") is not None
                else None
            ),
            scaled_score=float(payload["scaled_score"]),
            band=int(payload["band"]),
            has_latex=bool(payload["has_latex"]),
            base_score=(
                float(payload["base_score"])
                if payload.get("base_score") is not None
                else None
            ),
            note_reference=float(payload["note_reference"]),
            distractor_complexity=float(payload["distractor_complexity"]),
            processing_complexity=float(payload["processing_complexity"]),
            negative_stem=float(payload.get("negative_stem", 0.0)),
            cognitive_level=str(payload["cognitive_level"]),
            option_count=int(payload["option_count"]),
            topic_id=str(payload["topic_id"]),
            question_type=str(payload["question_type"]),
        )

    def to_dict(self) -> dict:
        return asdict(self)


def build_question_key(course_id: str, question: ImportedQuestion) -> str:
    stem = "|".join(
        [
            course_id.strip().lower(),
            question.topic_id.strip().lower(),
            question.question_text.strip().lower(),
        ]
    )
    digest = hashlib.sha1(stem.encode("utf-8")).hexdigest()[:12]
    topic_slug = _slugify(question.topic_id, default="topic")
    return f"{_slugify(course_id, default='course')}-{topic_slug}-{digest}"


def build_question_source_checksum(question: ImportedQuestion) -> str:
    payload = {
        "question_text": question.question_text,
        "options": question.options,
        "correct_option_text": question.correct_option_text,
        "short_explanation": question.short_explanation,
        "has_latex": question.has_latex,
        "question_type": question.question_type,
    }
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
