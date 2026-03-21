from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from scripts.import_question_bank import (
    DEFAULT_Q_AND_A_ROOT,
    discover_course_json_files,
    format_report_summary,
    import_courses,
)


@dataclass(slots=True)
class FakeReport:
    course_slug: str
    total_rows: int
    successful_rows: int
    failed_rows: int


class FakeImportService:
    def __init__(self):
        self.calls = []

    async def import_course_from_json(self, *, course_id: str, course_slug: str, json_path: Path):
        self.calls.append(
            {
                "course_id": course_id,
                "course_slug": course_slug,
                "json_path": json_path,
            }
        )
        return FakeReport(
            course_slug=course_slug,
            total_rows=10,
            successful_rows=9,
            failed_rows=1,
        )


def test_discover_course_json_files_skips_directories_without_scored_cleaned_json(tmp_path):
    (tmp_path / "linear-electronics").mkdir()
    (tmp_path / "linear-electronics" / "scored_cleaned.json").write_text("[]", encoding="utf-8")
    (tmp_path / "general-psychology").mkdir()
    (tmp_path / "scripts").mkdir()

    discovered = discover_course_json_files(tmp_path)

    assert discovered == {
        "linear-electronics": tmp_path / "linear-electronics" / "scored_cleaned.json"
    }


@pytest.mark.asyncio
async def test_import_courses_imports_all_discovered_courses(tmp_path):
    (tmp_path / "linear-electronics").mkdir()
    (tmp_path / "linear-electronics" / "scored_cleaned.json").write_text("[]", encoding="utf-8")
    (tmp_path / "thermodynamics").mkdir()
    (tmp_path / "thermodynamics" / "scored_cleaned.json").write_text("[]", encoding="utf-8")
    (tmp_path / "general-psychology").mkdir()

    service = FakeImportService()

    reports = await import_courses(
        service=service,
        q_and_a_root=tmp_path,
        import_all=True,
    )

    assert [report.course_slug for report in reports] == [
        "linear-electronics",
        "thermodynamics",
    ]
    assert [call["course_slug"] for call in service.calls] == [
        "linear-electronics",
        "thermodynamics",
    ]


@pytest.mark.asyncio
async def test_import_courses_raises_for_missing_specific_course(tmp_path):
    service = FakeImportService()

    with pytest.raises(ValueError, match="No scored_cleaned.json found"):
        await import_courses(
            service=service,
            q_and_a_root=tmp_path,
            course_slug="general-psychology",
        )


def test_format_report_summary_is_concise():
    report = FakeReport(
        course_slug="linear-electronics",
        total_rows=10,
        successful_rows=9,
        failed_rows=1,
    )

    assert format_report_summary(report) == "linear-electronics: total=10 ready=9 failed=1"


def test_default_q_and_a_root_points_to_shared_workspace_directory():
    assert DEFAULT_Q_AND_A_ROOT.name == "q_and_a"
