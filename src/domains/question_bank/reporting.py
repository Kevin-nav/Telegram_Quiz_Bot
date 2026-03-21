from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class QuestionImportResult:
    row_index: int
    status: str
    question_key: str | None = None
    errors: list[str] = field(default_factory=list)
    variant_count: int = 0


@dataclass(slots=True)
class CourseImportReport:
    course_id: str
    course_slug: str
    source_path: Path
    question_results: list[QuestionImportResult] = field(default_factory=list)

    @property
    def total_rows(self) -> int:
        return len(self.question_results)

    @property
    def successful_rows(self) -> int:
        return sum(1 for result in self.question_results if result.status == "ready")

    @property
    def failed_rows(self) -> int:
        return self.total_rows - self.successful_rows

    def add_result(self, result: QuestionImportResult) -> None:
        self.question_results.append(result)
