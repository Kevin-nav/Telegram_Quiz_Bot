from __future__ import annotations

from collections.abc import Sequence

from src.domains.catalog.service import CatalogService
from src.infra.db.repositories.question_bank_repository import QuestionBankRepository


class LearnerCatalogService:
    def __init__(
        self,
        catalog_service: CatalogService | None = None,
        question_bank_repository: QuestionBankRepository | None = None,
    ):
        self.catalog_service = catalog_service or CatalogService()
        self.question_bank_repository = question_bank_repository or QuestionBankRepository()

    async def get_faculties(self) -> list[dict]:
        return await self.catalog_service.get_faculties()

    async def get_programs(self, faculty_code: str) -> list[dict]:
        return await self.catalog_service.get_programs(faculty_code)

    async def get_levels(self, program_code: str) -> list[dict]:
        return await self.catalog_service.get_levels(program_code)

    async def get_semesters(self, program_code: str, level_code: str) -> list[dict]:
        return await self.catalog_service.get_semesters(program_code, level_code)

    async def get_courses(
        self,
        faculty_code: str,
        program_code: str,
        level_code: str,
        semester_code: str,
    ) -> list[dict]:
        courses = await self.catalog_service.get_courses(
            faculty_code,
            program_code,
            level_code,
            semester_code,
        )
        return await self._filter_courses_with_ready_questions(courses)

    async def _filter_courses_with_ready_questions(
        self,
        courses: Sequence[dict],
    ) -> list[dict]:
        course_codes = [
            course["code"]
            for course in courses
            if isinstance(course, dict) and course.get("code")
        ]
        if not course_codes:
            return []

        ready_course_codes = await self.question_bank_repository.list_course_ids_with_ready_questions(
            course_codes
        )
        if not ready_course_codes:
            return []

        return [
            course
            for course in courses
            if course.get("code") in ready_course_codes
        ]
