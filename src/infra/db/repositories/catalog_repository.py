from __future__ import annotations

from sqlalchemy import select

from src.infra.db.models.catalog_course import CatalogCourse
from src.infra.db.models.catalog_faculty import CatalogFaculty
from src.infra.db.models.catalog_level import CatalogLevel
from src.infra.db.models.catalog_program import CatalogProgram
from src.infra.db.models.catalog_semester import CatalogSemester
from src.infra.db.models.program_course_offering import ProgramCourseOffering
from src.infra.db.session import AsyncSessionLocal


class CatalogRepository:
    def __init__(self, session_factory=AsyncSessionLocal):
        self.session_factory = session_factory

    async def get_faculty(self, faculty_code: str) -> CatalogFaculty | None:
        async with self.session_factory() as session:
            result = await session.execute(
                select(CatalogFaculty).where(
                    CatalogFaculty.code == faculty_code,
                    CatalogFaculty.is_active.is_(True),
                )
            )
            return result.scalar_one_or_none()

    async def list_faculties(self) -> list[CatalogFaculty]:
        async with self.session_factory() as session:
            result = await session.execute(
                select(CatalogFaculty)
                .where(CatalogFaculty.is_active.is_(True))
                .order_by(CatalogFaculty.name.asc())
            )
            return list(result.scalars().all())

    async def get_program(self, program_code: str) -> CatalogProgram | None:
        async with self.session_factory() as session:
            result = await session.execute(
                select(CatalogProgram).where(
                    CatalogProgram.code == program_code,
                    CatalogProgram.is_active.is_(True),
                )
            )
            return result.scalar_one_or_none()

    async def list_programs(self, faculty_code: str | None = None) -> list[CatalogProgram]:
        async with self.session_factory() as session:
            stmt = select(CatalogProgram).where(CatalogProgram.is_active.is_(True))
            if faculty_code is not None:
                stmt = stmt.where(CatalogProgram.faculty_code == faculty_code)
            stmt = stmt.order_by(CatalogProgram.name.asc())
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def list_levels(self) -> list[CatalogLevel]:
        async with self.session_factory() as session:
            result = await session.execute(
                select(CatalogLevel)
                .where(CatalogLevel.is_active.is_(True))
                .order_by(CatalogLevel.code.asc())
            )
            return list(result.scalars().all())

    async def list_semesters(self) -> list[CatalogSemester]:
        async with self.session_factory() as session:
            result = await session.execute(
                select(CatalogSemester)
                .where(CatalogSemester.is_active.is_(True))
                .order_by(CatalogSemester.code.asc())
            )
            return list(result.scalars().all())

    async def list_courses(
        self,
        *,
        faculty_code: str | None = None,
        program_code: str | None = None,
        level_code: str | None = None,
        semester_code: str | None = None,
    ) -> list[CatalogCourse]:
        async with self.session_factory() as session:
            stmt = (
                select(CatalogCourse)
                .join(
                    ProgramCourseOffering,
                    ProgramCourseOffering.course_code == CatalogCourse.code,
                )
                .join(
                    CatalogProgram,
                    CatalogProgram.code == ProgramCourseOffering.program_code,
                )
                .where(
                    CatalogCourse.is_active.is_(True),
                    ProgramCourseOffering.is_active.is_(True),
                    CatalogProgram.is_active.is_(True),
                )
            )

            if faculty_code is not None:
                stmt = stmt.where(CatalogProgram.faculty_code == faculty_code)
            if program_code is not None:
                stmt = stmt.where(ProgramCourseOffering.program_code == program_code)
            if level_code is not None:
                stmt = stmt.where(ProgramCourseOffering.level_code == level_code)
            if semester_code is not None:
                stmt = stmt.where(ProgramCourseOffering.semester_code == semester_code)

            stmt = stmt.order_by(CatalogCourse.name.asc())
            result = await session.execute(stmt)
            return list(result.scalars().unique().all())
