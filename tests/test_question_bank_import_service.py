from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.domains.question_bank.import_service import QuestionBankImportService


class FakeQuestionRecord:
    def __init__(self, payload: dict, record_id: int):
        self.id = record_id
        self.payload = payload


class FakeRepository:
    def __init__(self):
        self.upserts = []
        self.status_updates = []
        self.variant_replacements = []
        self._records = {}
        self._next_id = 1

    async def upsert_question(self, payload: dict):
        self.upserts.append(payload)
        question_key = payload["question_key"]
        existing = self._records.get(question_key)
        if existing is None:
            existing = FakeQuestionRecord(payload, self._next_id)
            self._next_id += 1
            self._records[question_key] = existing
        else:
            existing.payload = payload
        return existing

    async def update_question_status(self, question_key: str, **kwargs):
        self.status_updates.append((question_key, kwargs))
        return self._records.get(question_key)

    async def replace_asset_variants(self, question_id: int, variants: list[dict]):
        self.variant_replacements.append((question_id, variants))
        return variants


class FakeAssetService:
    def __init__(self):
        self.variant_uploads = []
        self.explanation_uploads = []

    def upload_question_variant(self, **kwargs):
        self.variant_uploads.append(kwargs)
        variant_index = kwargs["variant_index"]
        version = kwargs["version"]
        question_key = kwargs["question_key"]
        course_slug = kwargs["course_slug"]
        return type(
            "Uploaded",
            (),
            {
                "key": f"questions/{course_slug}/{question_key}/{version}/question_variant_{variant_index}.png",
                "url": f"https://cdn.example.com/questions/{course_slug}/{question_key}/{version}/question_variant_{variant_index}.png",
            },
        )()

    def upload_explanation_image(self, **kwargs):
        self.explanation_uploads.append(kwargs)
        version = kwargs["version"]
        question_key = kwargs["question_key"]
        course_slug = kwargs["course_slug"]
        return type(
            "Uploaded",
            (),
            {
                "key": f"questions/{course_slug}/{question_key}/{version}/explanation.png",
                "url": f"https://cdn.example.com/questions/{course_slug}/{question_key}/{version}/explanation.png",
            },
        )()


def fake_question_renderer(question_text: str, options: list[str]) -> str:
    return f"QUESTION::{question_text}::{','.join(options)}"


def fake_explanation_renderer(correct_option_text: str, explanation_text: str) -> str:
    return f"EXPLANATION::{correct_option_text}::{explanation_text}"


def fake_variant_builder(options: list[str]) -> list[list[str]]:
    return [
        options,
        [options[1], options[0], options[2], options[3]],
        [options[2], options[3], options[0], options[1]],
        [options[3], options[2], options[1], options[0]],
    ]


def fake_variant_order_builder(option_count: int) -> list[list[int]]:
    assert option_count == 4
    return [[0, 1, 2, 3], [1, 0, 2, 3], [2, 3, 0, 1], [3, 2, 1, 0]]


def fake_latex_to_png_renderer(latex_content: str, output_path: str) -> bool:
    Path(output_path).write_bytes(latex_content.encode("utf-8"))
    return True


@pytest.mark.asyncio
async def test_import_service_continues_after_invalid_row_and_imports_valid_rows(tmp_path):
    json_path = tmp_path / "scored_cleaned.json"
    payload = [
        {
            "question_text": "What is Ohm's law?",
            "options": ["V = IR", "P = IV", "Q = CV", "F = ma"],
            "correct_option_text": "V = IR",
            "short_explanation": "Voltage equals current times resistance.",
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
        },
        {
            "question_text": "Broken question",
            "options": ["A", "B", "C", "D"],
            "correct_option_text": "Z",
            "short_explanation": "Broken.",
            "raw_score": 1.0,
            "scaled_score": 1.2,
            "band": 1,
            "has_latex": False,
            "base_score": 1.0,
            "note_reference": 1.0,
            "distractor_complexity": 1.0,
            "processing_complexity": 1.0,
            "negative_stem": 1.0,
            "cognitive_level": "Understanding",
            "option_count": 4,
            "topic_id": "broken",
            "question_type": "MCQ",
        },
        {
            "question_text": "Solve $x+1=2$",
            "options": ["1", "2", "3", "4"],
            "correct_option_text": "1",
            "short_explanation": "Because $x=1$.",
            "raw_score": 2.3,
            "scaled_score": 1.7,
            "band": 1,
            "has_latex": True,
            "base_score": 1.5,
            "note_reference": 1.0,
            "distractor_complexity": 1.1,
            "processing_complexity": 1.0,
            "negative_stem": 1.0,
            "cognitive_level": "Applying",
            "option_count": 4,
            "topic_id": "algebra",
            "question_type": "MCQ",
        },
    ]
    json_path.write_text(json.dumps(payload), encoding="utf-8")

    repository = FakeRepository()
    asset_service = FakeAssetService()
    service = QuestionBankImportService(
        repository=repository,
        asset_service=asset_service,
        question_renderer=fake_question_renderer,
        explanation_renderer=fake_explanation_renderer,
        variant_builder=fake_variant_builder,
        variant_order_builder=fake_variant_order_builder,
        latex_to_png_renderer=fake_latex_to_png_renderer,
    )

    report = await service.import_course_from_json(
        course_id="linear-electronics",
        course_slug="linear-electronics",
        json_path=json_path,
    )

    assert report.total_rows == 3
    assert report.successful_rows == 2
    assert report.failed_rows == 1
    assert [result.status for result in report.question_results] == [
        "ready",
        "invalid",
        "ready",
    ]
    assert len(repository.upserts) == 2
    assert len(asset_service.variant_uploads) == 4
    assert len(asset_service.explanation_uploads) == 1
    assert len(repository.variant_replacements) == 1
    assert report.question_results[2].variant_count == 4


@pytest.mark.asyncio
async def test_import_service_marks_latex_row_error_when_render_fails(tmp_path):
    json_path = tmp_path / "scored_cleaned.json"
    json_path.write_text(
        json.dumps(
            [
                {
                    "question_text": "Solve $x+1=2$",
                    "options": ["1", "2", "3", "4"],
                    "correct_option_text": "1",
                    "short_explanation": "Because $x=1$.",
                    "raw_score": 2.3,
                    "scaled_score": 1.7,
                    "band": 1,
                    "has_latex": True,
                    "base_score": 1.5,
                    "note_reference": 1.0,
                    "distractor_complexity": 1.1,
                    "processing_complexity": 1.0,
                    "negative_stem": 1.0,
                    "cognitive_level": "Applying",
                    "option_count": 4,
                    "topic_id": "algebra",
                    "question_type": "MCQ",
                }
            ]
        ),
        encoding="utf-8",
    )

    service = QuestionBankImportService(
        repository=FakeRepository(),
        asset_service=FakeAssetService(),
        question_renderer=fake_question_renderer,
        explanation_renderer=fake_explanation_renderer,
        variant_builder=fake_variant_builder,
        variant_order_builder=fake_variant_order_builder,
        latex_to_png_renderer=lambda *_args, **_kwargs: False,
    )

    report = await service.import_course_from_json(
        course_id="linear-electronics",
        json_path=json_path,
    )

    assert report.total_rows == 1
    assert report.question_results[0].status == "error"
    assert "latex render failed" in report.question_results[0].errors[0]
