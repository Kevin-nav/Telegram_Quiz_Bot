from __future__ import annotations

import pytest

from src.infra.db.models.question_report import QuestionReport
from src.infra.db.repositories.question_report_repository import QuestionReportRepository


class FakeSession:
    def __init__(self):
        self.records: list[QuestionReport] = []
        self.id_seq = 1

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def add(self, record):
        if not isinstance(record, QuestionReport):
            raise AssertionError(f"Unsupported record type: {type(record)!r}")
        if record.id is None:
            record.id = self.id_seq
            self.id_seq += 1
        self.records.append(record)

    async def commit(self):
        return None

    async def refresh(self, record):
        return None


class FakeSessionFactory:
    def __init__(self, session: FakeSession):
        self.session = session

    def __call__(self):
        return self.session


@pytest.mark.asyncio
async def test_create_report_persists_scope_reason_note_and_metadata():
    session = FakeSession()
    repository = QuestionReportRepository(FakeSessionFactory(session))

    report = await repository.create_report(
        {
            "user_id": 42,
            "session_id": "session-1",
            "course_id": "linear-electronics",
            "question_id": 17,
            "question_key": "linear-electronics-q1",
            "question_index": 0,
            "report_scope": "answer",
            "report_reason": "correct_answer_shown_is_wrong",
            "report_note": "Option B is the correct answer here.",
            "report_metadata": {
                "selected_option_text": "A",
                "correct_option_text": "B",
                "has_latex": False,
            },
        }
    )

    assert report.id == 1
    assert report.report_scope == "answer"
    assert report.report_reason == "correct_answer_shown_is_wrong"
    assert report.report_note == "Option B is the correct answer here."
    assert report.report_metadata["correct_option_text"] == "B"
    assert session.records[0] is report
