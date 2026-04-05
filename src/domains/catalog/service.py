from __future__ import annotations

from src.cache import redis_client
from src.infra.db.repositories.catalog_repository import CatalogRepository
from src.infra.redis.state_store import InteractiveStateStore


class CatalogService:
    def __init__(
        self,
        repository: CatalogRepository | None = None,
        state_store: InteractiveStateStore | None = None,
        allowed_course_codes: tuple[str, ...] = (),
        fixed_faculty_code: str | None = None,
        fixed_level_code: str | None = None,
    ):
        self.repository = repository or CatalogRepository()
        self.state_store = state_store or InteractiveStateStore(redis_client)
        self.allowed_course_codes = allowed_course_codes
        self.fixed_faculty_code = fixed_faculty_code
        self.fixed_level_code = fixed_level_code

    async def get_faculties(self) -> list[dict]:
        cached = await self.state_store.get_catalog_faculties()
        if cached is not None:
            return cached

        faculties = await self.repository.list_faculties()
        payload = [
            self._to_faculty_dict(faculty)
            for faculty in faculties
            if self._faculty_is_allowed(faculty.code)
        ]
        await self.state_store.cache_catalog_faculties(payload)
        return payload

    async def get_programs(self, faculty_code: str) -> list[dict]:
        cached = await self.state_store.get_catalog_programs(faculty_code)
        if cached is not None:
            return cached

        faculty = await self.repository.get_faculty(faculty_code)
        if faculty is None or not self._faculty_is_allowed(faculty_code):
            return []

        programs = await self.repository.list_programs(faculty_code=faculty_code)
        payload = [self._to_program_dict(program) for program in programs]
        await self.state_store.cache_catalog_programs(faculty_code, payload)
        return payload

    async def get_levels(self, program_code: str) -> list[dict]:
        cached = await self.state_store.get_catalog_levels(program_code)
        if cached is not None:
            return cached

        program = await self.repository.get_program(program_code)
        if program is None:
            return []

        levels = await self.repository.list_levels()
        payload = [
            self._to_level_dict(level)
            for level in levels
            if self._level_is_allowed(level.code)
        ]
        await self.state_store.cache_catalog_levels(program_code, payload)
        return payload

    async def get_semesters(self, program_code: str, level_code: str) -> list[dict]:
        cached = await self.state_store.get_catalog_semesters(program_code, level_code)
        if cached is not None:
            return cached

        courses = await self.repository.list_courses(
            program_code=program_code,
            level_code=level_code,
        )
        if not courses:
            await self.state_store.cache_catalog_semesters(program_code, level_code, [])
            return []

        semesters = await self.repository.list_semesters()
        payload = [self._to_semester_dict(semester) for semester in semesters]
        await self.state_store.cache_catalog_semesters(program_code, level_code, payload)
        return payload

    async def get_courses(
        self,
        faculty_code: str,
        program_code: str,
        level_code: str,
        semester_code: str,
    ) -> list[dict]:
        cached = await self.state_store.get_catalog_courses(
            faculty_code,
            program_code,
            level_code,
            semester_code,
        )
        if cached is not None:
            return cached

        if not self._faculty_is_allowed(faculty_code) or not self._level_is_allowed(
            level_code
        ):
            return []

        faculty = await self.repository.get_faculty(faculty_code)
        if faculty is None:
            return []

        programs = await self.repository.list_programs(faculty_code=faculty_code)
        if not any(program.code == program_code for program in programs):
            return []

        courses = await self.repository.list_courses(
            faculty_code=faculty_code,
            program_code=program_code,
            level_code=level_code,
            semester_code=semester_code,
        )
        payload = [
            self._to_course_dict(course, level_code, semester_code)
            for course in courses
            if self._course_is_allowed(course.code)
        ]
        await self.state_store.cache_catalog_courses(
            faculty_code,
            program_code,
            level_code,
            semester_code,
            payload,
        )
        return payload

    def _to_faculty_dict(self, faculty) -> dict:
        return {"code": faculty.code, "name": faculty.name}

    def _to_program_dict(self, program) -> dict:
        return {"code": program.code, "name": program.name}

    def _to_level_dict(self, level) -> dict:
        return {"code": level.code, "name": level.name}

    def _to_semester_dict(self, semester) -> dict:
        return {
            "code": semester.code,
            "name": semester.name,
            "active": bool(getattr(semester, "is_active", True)),
        }

    def _to_course_dict(self, course, level_code: str, semester_code: str) -> dict:
        return {
            "code": course.code,
            "name": course.name,
            "level_code": level_code,
            "semester_code": semester_code,
        }

    def _course_is_allowed(self, course_code: str | None) -> bool:
        if not self.allowed_course_codes or not course_code:
            return True
        return course_code in self.allowed_course_codes

    def _faculty_is_allowed(self, faculty_code: str | None) -> bool:
        if not self.fixed_faculty_code or not faculty_code:
            return True
        return faculty_code == self.fixed_faculty_code

    def _level_is_allowed(self, level_code: str | None) -> bool:
        if not self.fixed_level_code or not level_code:
            return True
        return level_code == self.fixed_level_code
