from src.domains.catalog.data import FACULTIES, LEVELS, PROGRAM_COURSES, SEMESTERS
from src.domains.catalog.service import CatalogService


class CatalogNavigationService:
    def __init__(self, catalog_service: CatalogService | None = None):
        self.catalog_service = catalog_service

    def get_faculties(self) -> list[dict]:
        return [
            {"code": faculty["code"], "name": faculty["name"]}
            for faculty in FACULTIES
        ]

    def get_programs(self, faculty_code: str) -> list[dict]:
        faculty = self._get_faculty(faculty_code)
        if faculty is None:
            return []

        return [
            {"code": program["code"], "name": program["name"]}
            for program in faculty["programs"]
        ]

    def get_levels(self, program_code: str) -> list[dict]:
        if not self._program_exists(program_code):
            return []
        return LEVELS.copy()

    def get_semesters(self, program_code: str, level_code: str) -> list[dict]:
        if not self._program_exists(program_code):
            return []
        if not any(
            course["level_code"] == level_code
            for course in PROGRAM_COURSES.get(program_code, [])
        ):
            return []
        return SEMESTERS.copy()

    def get_courses(
        self,
        faculty_code: str,
        program_code: str,
        level_code: str,
        semester_code: str,
    ) -> list[dict]:
        faculty = self._get_faculty(faculty_code)
        if faculty is None:
            return []

        if not any(program["code"] == program_code for program in faculty["programs"]):
            return []

        return [
            course
            for course in PROGRAM_COURSES.get(program_code, [])
            if course["level_code"] == level_code
            and course["semester_code"] == semester_code
        ]

    def _get_faculty(self, faculty_code: str) -> dict | None:
        for faculty in FACULTIES:
            if faculty["code"] == faculty_code:
                return faculty
        return None

    def _program_exists(self, program_code: str) -> bool:
        return any(
            program["code"] == program_code
            for faculty in FACULTIES
            for program in faculty["programs"]
        )

    async def get_faculties_db(self) -> list[dict]:
        return await self._catalog_service().get_faculties()

    async def get_programs_db(self, faculty_code: str) -> list[dict]:
        return await self._catalog_service().get_programs(faculty_code)

    async def get_levels_db(self, program_code: str) -> list[dict]:
        return await self._catalog_service().get_levels(program_code)

    async def get_semesters_db(self, program_code: str, level_code: str) -> list[dict]:
        return await self._catalog_service().get_semesters(program_code, level_code)

    async def get_courses_db(
        self,
        faculty_code: str,
        program_code: str,
        level_code: str,
        semester_code: str,
    ) -> list[dict]:
        return await self._catalog_service().get_courses(
            faculty_code,
            program_code,
            level_code,
            semester_code,
        )

    def _catalog_service(self) -> CatalogService:
        return self.catalog_service or CatalogService()
