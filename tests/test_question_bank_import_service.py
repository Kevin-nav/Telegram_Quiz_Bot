from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.bot.runtime_config import DEFAULT_BOT_THEMES, BotRuntimeConfig
from src.domains.question_bank.import_service import QuestionBankImportService
from src.domains.question_bank.schemas import ImportedQuestion, build_question_key


class FakeQuestionRecord:
    def __init__(self, payload: dict, record_id: int):
        self.id = record_id
        self.apply_payload(payload)

    def apply_payload(self, payload: dict) -> None:
        self.payload = dict(payload)
        for key, value in payload.items():
            setattr(self, key, value)


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
            existing.apply_payload(payload)
        return existing

    async def update_question_status(self, question_key: str, **kwargs):
        self.status_updates.append((question_key, kwargs))
        record = self._records.get(question_key)
        if record is not None:
            record.apply_payload({**record.payload, **kwargs})
        return record

    async def get_question(self, question_key: str):
        return self._records.get(question_key)

    async def replace_asset_variants(
        self,
        question_id: int,
        variants: list[dict],
        *,
        bot_id: str = "tanjah",
    ):
        self.variant_replacements.append((question_id, variants))
        return variants


class FakeAssetService:
    def __init__(self):
        self.variant_uploads = []
        self.explanation_uploads = []

    def upload_question_variant(self, **kwargs):
        self.variant_uploads.append(kwargs)
        bot_id = kwargs.get("bot_id", "tanjah")
        variant_index = kwargs["variant_index"]
        version = kwargs["version"]
        question_key = kwargs["question_key"]
        course_slug = kwargs["course_slug"]
        bot_prefix = "" if bot_id == "tanjah" else f"{bot_id}/"
        return type(
            "Uploaded",
            (),
            {
                "key": f"questions/{bot_prefix}{course_slug}/{question_key}/{version}/question_variant_{variant_index}.png",
                "url": f"https://cdn.example.com/questions/{bot_prefix}{course_slug}/{question_key}/{version}/question_variant_{variant_index}.png",
            },
        )()

    def upload_explanation_image(self, **kwargs):
        self.explanation_uploads.append(kwargs)
        bot_id = kwargs.get("bot_id", "tanjah")
        version = kwargs["version"]
        question_key = kwargs["question_key"]
        course_slug = kwargs["course_slug"]
        bot_prefix = "" if bot_id == "tanjah" else f"{bot_id}/"
        return type(
            "Uploaded",
            (),
            {
                "key": f"questions/{bot_prefix}{course_slug}/{question_key}/{version}/explanation.png",
                "url": f"https://cdn.example.com/questions/{bot_prefix}{course_slug}/{question_key}/{version}/explanation.png",
            },
        )()


def fake_question_renderer(question_text: str, options: list[str], bot_theme=None) -> str:
    brand_name = getattr(bot_theme, "brand_name", "Tanjah")
    return f"QUESTION::{brand_name}::{question_text}::{','.join(options)}"


def fake_explanation_renderer(
    correct_option_text: str,
    explanation_text: str,
    bot_theme=None,
) -> str:
    brand_name = getattr(bot_theme, "brand_name", "Tanjah")
    return f"EXPLANATION::{brand_name}::{correct_option_text}::{explanation_text}"


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


def make_base_row(**overrides):
    payload = {
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
    }
    payload.update(overrides)
    return payload


@pytest.mark.asyncio
async def test_import_service_continues_after_invalid_row_and_imports_valid_rows(tmp_path):
    json_path = tmp_path / "scored_cleaned.json"
    payload = [
        make_base_row(),
        make_base_row(
            question_text="Broken question",
            options=["A", "B", "C", "D"],
            correct_option_text="Z",
            short_explanation="Broken.",
            raw_score=1.0,
            scaled_score=1.2,
            base_score=1.0,
            distractor_complexity=1.0,
            topic_id="broken",
        ),
        make_base_row(
            question_text="Solve $x+1=2$",
            options=["1", "2", "3", "4"],
            correct_option_text="1",
            short_explanation="Because $x=1$.",
            raw_score=2.3,
            scaled_score=1.7,
            has_latex=True,
            base_score=1.5,
            topic_id="algebra",
            cognitive_level="Applying",
        ),
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
async def test_import_service_infers_tf_distractor_complexity_from_statement_clarity(
    tmp_path,
):
    json_path = tmp_path / "scored_cleaned.json"
    row = make_base_row(
        options=["True", "False"],
        correct_option_text="True",
        option_count=2,
        question_type="T/F",
        negative_stem=0.0,
        distractor_complexity=1.2,
        statement_clarity=1.2,
    )
    row.pop("distractor_complexity")
    json_path.write_text(
        json.dumps([row]),
        encoding="utf-8",
    )

    repository = FakeRepository()
    service = QuestionBankImportService(
        repository=repository,
        asset_service=FakeAssetService(),
        question_renderer=fake_question_renderer,
        explanation_renderer=fake_explanation_renderer,
        variant_builder=fake_variant_builder,
        variant_order_builder=fake_variant_order_builder,
        latex_to_png_renderer=fake_latex_to_png_renderer,
    )

    report = await service.import_course_from_json(
        course_id="instruments-and-measurements",
        course_slug="instruments-and-measurements",
        json_path=json_path,
    )

    assert report.successful_rows == 1
    assert repository.upserts[0]["distractor_complexity"] == 1.2


@pytest.mark.asyncio
async def test_import_service_marks_latex_row_error_when_render_fails(tmp_path):
    json_path = tmp_path / "scored_cleaned.json"
    json_path.write_text(
        json.dumps([
            make_base_row(
                question_text="Solve $x+1=2$",
                options=["1", "2", "3", "4"],
                correct_option_text="1",
                short_explanation="Because $x=1$.",
                raw_score=2.3,
                scaled_score=1.7,
                has_latex=True,
                base_score=1.5,
                topic_id="algebra",
                cognitive_level="Applying",
            )
        ]),
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


@pytest.mark.asyncio
async def test_import_service_promotes_oversized_poll_question_to_latex(tmp_path):
    json_path = tmp_path / "scored_cleaned.json"
    json_path.write_text(
        json.dumps([
            make_base_row(
                question_text="Q" * 301,
                has_latex=False,
            )
        ]),
        encoding="utf-8",
    )

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

    assert report.successful_rows == 1
    assert repository.upserts[0]["has_latex"] is True
    assert repository.upserts[0]["status"] == "processing"
    assert len(asset_service.variant_uploads) == 4
    assert len(asset_service.explanation_uploads) == 1
    assert len(repository.variant_replacements) == 1


@pytest.mark.asyncio
async def test_import_service_reprocesses_existing_non_latex_row_when_option_exceeds_poll_limit(
    tmp_path,
):
    json_path = tmp_path / "scored_cleaned.json"
    oversized_option = "A" * 101
    json_path.write_text(
        json.dumps([
            make_base_row(
                options=[oversized_option, "P = IV", "Q = CV", "F = ma"],
                correct_option_text=oversized_option,
                has_latex=False,
            )
        ]),
        encoding="utf-8",
    )

    repository = FakeRepository()
    existing_row = make_base_row(
        options=[oversized_option, "P = IV", "Q = CV", "F = ma"],
        correct_option_text=oversized_option,
        has_latex=False,
    )
    question_key = build_question_key(
        "linear-electronics",
        ImportedQuestion.from_dict(existing_row),
    )
    existing_payload = {
        **existing_row,
        "question_key": question_key,
        "course_id": "linear-electronics",
        "course_slug": "linear-electronics",
        "source_checksum": "old-non-latex-checksum",
        "status": "ready",
        "variant_count": 0,
    }
    repository._records[question_key] = FakeQuestionRecord(existing_payload, 1)
    repository._next_id = 2

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

    assert report.successful_rows == 1
    assert len(repository.upserts) == 1
    assert repository.upserts[0]["question_key"] == question_key
    assert repository.upserts[0]["has_latex"] is True
    assert repository.upserts[0]["source_checksum"] != "old-non-latex-checksum"
    assert repository.status_updates[-1][1]["status"] == "ready"
    assert len(asset_service.variant_uploads) == 4


@pytest.mark.asyncio
async def test_import_service_generates_bot_specific_latex_assets_and_explanation_maps(
    tmp_path,
):
    json_path = tmp_path / "scored_cleaned.json"
    json_path.write_text(
        json.dumps(
            [
                make_base_row(
                    question_text="Solve $x+1=2$",
                    options=["1", "2", "3", "4"],
                    correct_option_text="1",
                    short_explanation="Because $x=1$.",
                    has_latex=True,
                )
            ]
        ),
        encoding="utf-8",
    )

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
        bot_configs={
            "tanjah": BotRuntimeConfig(
                bot_id="tanjah",
                telegram_bot_token="tanjah-token",
                webhook_secret="tanjah-secret",
                webhook_path="/webhook/tanjah",
                allowed_course_codes=(),
                theme=DEFAULT_BOT_THEMES["tanjah"],
            ),
            "adarkwa": BotRuntimeConfig(
                bot_id="adarkwa",
                telegram_bot_token="adarkwa-token",
                webhook_secret="adarkwa-secret",
                webhook_path="/webhook/adarkwa",
                allowed_course_codes=("linear-algebra",),
                theme=DEFAULT_BOT_THEMES["adarkwa"],
            ),
        },
    )

    report = await service.import_course_from_json(
        course_id="linear-electronics",
        course_slug="linear-electronics",
        json_path=json_path,
    )

    assert report.successful_rows == 1
    assert {upload["bot_id"] for upload in asset_service.variant_uploads} == {
        "tanjah",
        "adarkwa",
    }
    assert {upload["bot_id"] for upload in asset_service.explanation_uploads} == {
        "tanjah",
        "adarkwa",
    }
    assert len(repository.variant_replacements) == 2

    _, tanjah_variants = repository.variant_replacements[0]
    _, adarkwa_variants = repository.variant_replacements[1]
    assert {variant["bot_id"] for variant in tanjah_variants} == {"tanjah"}
    assert {variant["bot_id"] for variant in adarkwa_variants} == {"adarkwa"}

    question_key, status_payload = repository.status_updates[-1]
    assert question_key == report.question_results[0].question_key
    assert status_payload["status"] == "ready"
    assert status_payload["explanation_asset_urls_by_bot"] == {
        "tanjah": (
            f"https://cdn.example.com/questions/linear-electronics/"
            f"{report.question_results[0].question_key}/"
            f"{repository.upserts[0]['source_checksum']}/explanation.png"
        ),
        "adarkwa": (
            f"https://cdn.example.com/questions/adarkwa/linear-electronics/"
            f"{report.question_results[0].question_key}/"
            f"{repository.upserts[0]['source_checksum']}/explanation.png"
        ),
    }
