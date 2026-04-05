from __future__ import annotations

import pytest

from src.infra.db.models.question_asset_variant import QuestionAssetVariant
from src.infra.db.models.question_bank import QuestionBank
from src.infra.db.repositories.question_bank_repository import QuestionBankRepository


class FakeScalarResult:
    def __init__(self, values):
        self._values = values

    def all(self):
        return list(self._values)


class FakeResult:
    def __init__(self, value=None, values=None):
        self._value = value
        self._values = values or []

    def scalar_one_or_none(self):
        return self._value

    def scalars(self):
        return FakeScalarResult(self._values)


class FakeSession:
    def __init__(self):
        self.questions_by_key: dict[str, QuestionBank] = {}
        self.variants_by_question_id: dict[int, list[QuestionAssetVariant]] = {}
        self.question_id_seq = 1
        self.variant_id_seq = 1

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def execute(self, statement):
        statement_type = statement.__visit_name__
        params = statement.compile().params

        if statement_type == "select":
            model = statement.column_descriptions[0]["entity"]
            if model is QuestionBank:
                if "question_key_1" in params:
                    return FakeResult(self.questions_by_key.get(params["question_key_1"]))

                course_id = params.get("course_id_1")
                status = params.get("status_1")
                values = [
                    question
                    for question in self.questions_by_key.values()
                    if question.course_id == course_id and question.status == status
                ]
                values.sort(key=lambda question: question.id or 0)
                return FakeResult(values=values)

        if statement_type == "delete":
            question_id = params["question_id_1"]
            bot_id = params.get("bot_id_1")
            if bot_id is None:
                self.variants_by_question_id[question_id] = []
            else:
                self.variants_by_question_id[question_id] = [
                    variant
                    for variant in self.variants_by_question_id.get(question_id, [])
                    if getattr(variant, "bot_id", "tanjah") != bot_id
                ]
            return FakeResult()

        raise AssertionError(f"Unsupported statement: {statement_type}")

    def add(self, record):
        if isinstance(record, QuestionBank):
            if record.id is None:
                record.id = self.question_id_seq
                self.question_id_seq += 1
            self.questions_by_key[record.question_key] = record
            return

        if isinstance(record, QuestionAssetVariant):
            if record.id is None:
                record.id = self.variant_id_seq
                self.variant_id_seq += 1
            self.variants_by_question_id.setdefault(record.question_id, []).append(record)
            return

        raise AssertionError(f"Unsupported record type: {type(record)!r}")

    def add_all(self, records):
        for record in records:
            self.add(record)

    async def commit(self):
        return None

    async def refresh(self, record):
        return None


class FakeSessionFactory:
    def __init__(self, session: FakeSession):
        self.session = session

    def __call__(self):
        return self.session


def make_question_payload(**overrides) -> dict:
    payload = {
        "question_key": "linear-electronics-op-amp-001",
        "course_id": "linear-electronics",
        "course_slug": "linear-electronics",
        "question_text": "An ideal op-amp is characterised by",
        "options": ["A", "B", "C", "D"],
        "correct_option_text": "B",
        "short_explanation": "Ideal op-amps have infinite gain and input resistance.",
        "question_type": "MCQ",
        "option_count": 4,
        "has_latex": False,
        "raw_score": 1.95,
        "scaled_score": 1.5,
        "base_score": 1.3,
        "band": 1,
        "topic_id": "op_amp_basics",
        "cognitive_level": "Understanding",
        "processing_complexity": 1.0,
        "distractor_complexity": 1.5,
        "note_reference": 1.0,
        "negative_stem": 1.0,
        "status": "draft",
        "source_checksum": "source-1",
        "render_checksum": None,
        "explanation_asset_key": None,
        "explanation_asset_url": None,
        "variant_count": 0,
    }
    payload.update(overrides)
    return payload


@pytest.mark.asyncio
async def test_upsert_question_returns_existing_row_for_same_question_key():
    session = FakeSession()
    repository = QuestionBankRepository(FakeSessionFactory(session))

    created = await repository.upsert_question(make_question_payload())
    updated = await repository.upsert_question(
        make_question_payload(status="ready", scaled_score=2.1)
    )

    assert created.id == updated.id
    assert updated.status == "ready"
    assert updated.scaled_score == 2.1


@pytest.mark.asyncio
async def test_replace_asset_variants_replaces_existing_records_for_question():
    session = FakeSession()
    repository = QuestionBankRepository(FakeSessionFactory(session))
    question = await repository.upsert_question(make_question_payload(has_latex=True))

    initial = await repository.replace_asset_variants(
        question.id,
        [
            {
                "bot_id": "tanjah",
                "variant_index": 0,
                "option_order": [0, 1, 2, 3],
                "question_asset_key": "questions/q0.png",
                "question_asset_url": "https://cdn.example/q0.png",
                "render_checksum": "r0",
            }
        ],
    )
    replaced = await repository.replace_asset_variants(
        question.id,
        [
            {
                "bot_id": "tanjah",
                "variant_index": 1,
                "option_order": [1, 0, 3, 2],
                "question_asset_key": "questions/q1.png",
                "question_asset_url": "https://cdn.example/q1.png",
                "render_checksum": "r1",
            }
        ],
    )

    assert len(initial) == 1
    assert len(replaced) == 1
    assert session.variants_by_question_id[question.id][0].variant_index == 1


@pytest.mark.asyncio
async def test_replace_asset_variants_only_replaces_rows_for_matching_bot_id():
    session = FakeSession()
    repository = QuestionBankRepository(FakeSessionFactory(session))
    question = await repository.upsert_question(make_question_payload(has_latex=True))

    await repository.replace_asset_variants(
        question.id,
        [
            {
                "bot_id": "tanjah",
                "variant_index": 0,
                "option_order": [0, 1, 2, 3],
                "question_asset_key": "questions/tanjah-v0.png",
                "question_asset_url": "https://cdn.example/tanjah-v0.png",
                "render_checksum": "r0",
            }
        ],
        bot_id="tanjah",
    )
    await repository.replace_asset_variants(
        question.id,
        [
            {
                "bot_id": "adarkwa",
                "variant_index": 0,
                "option_order": [0, 1, 2, 3],
                "question_asset_key": "questions/adarkwa-v0.png",
                "question_asset_url": "https://cdn.example/adarkwa-v0.png",
                "render_checksum": "r1",
            }
        ],
        bot_id="adarkwa",
    )

    bot_ids = [
        variant.bot_id
        for variant in session.variants_by_question_id[question.id]
    ]
    assert bot_ids == ["tanjah", "adarkwa"]


@pytest.mark.asyncio
async def test_list_ready_questions_and_update_question_status():
    session = FakeSession()
    repository = QuestionBankRepository(FakeSessionFactory(session))
    await repository.upsert_question(make_question_payload(question_key="ready-q", status="ready"))
    await repository.upsert_question(make_question_payload(question_key="draft-q", status="draft"))

    ready_questions = await repository.list_ready_questions("linear-electronics")
    updated = await repository.update_question_status(
        "draft-q",
        status="ready",
        source_checksum="source-2",
        render_checksum="render-2",
        explanation_asset_key="questions/explanation.png",
        explanation_asset_url="https://cdn.example/explanation.png",
        variant_count=4,
    )

    assert [question.question_key for question in ready_questions] == ["ready-q"]
    assert updated is not None
    assert updated.status == "ready"
    assert updated.variant_count == 4
    assert updated.explanation_asset_key == "questions/explanation.png"
