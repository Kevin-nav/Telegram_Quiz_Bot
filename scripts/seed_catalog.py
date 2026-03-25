from __future__ import annotations

import asyncio
import logging
import sys

from sqlalchemy import select

from src.domains.catalog.data import build_catalog_seed_payload
from src.infra.db.models.catalog_course import CatalogCourse
from src.infra.db.models.catalog_faculty import CatalogFaculty
from src.infra.db.models.catalog_level import CatalogLevel
from src.infra.db.models.catalog_program import CatalogProgram
from src.infra.db.models.catalog_semester import CatalogSemester
from src.infra.db.models.program_course_offering import ProgramCourseOffering
from src.infra.db.session import AsyncSessionLocal


log = logging.getLogger(__name__)


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-7s  %(name)s  %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stderr,
    )


async def upsert_by_code(session, model, payload: dict):
    record = await session.scalar(select(model).where(model.code == payload["code"]))
    if record is None:
        record = model(**payload)
        session.add(record)
        return

    for key, value in payload.items():
        setattr(record, key, value)


async def upsert_offering(session, payload: dict) -> None:
    record = await session.scalar(
        select(ProgramCourseOffering).where(
            ProgramCourseOffering.program_code == payload["program_code"],
            ProgramCourseOffering.level_code == payload["level_code"],
            ProgramCourseOffering.semester_code == payload["semester_code"],
            ProgramCourseOffering.course_code == payload["course_code"],
        )
    )
    if record is None:
        session.add(ProgramCourseOffering(**payload))
        return

    for key, value in payload.items():
        setattr(record, key, value)


async def async_main() -> int:
    payload = build_catalog_seed_payload()

    async with AsyncSessionLocal() as session:
        for faculty in payload["faculties"]:
            await upsert_by_code(session, CatalogFaculty, faculty)
        for level in payload["levels"]:
            await upsert_by_code(session, CatalogLevel, level)
        for semester in payload["semesters"]:
            await upsert_by_code(session, CatalogSemester, semester)
        for course in payload["courses"]:
            await upsert_by_code(session, CatalogCourse, course)
        for program in payload["programs"]:
            await upsert_by_code(session, CatalogProgram, program)
        for offering in payload["offerings"]:
            await upsert_offering(session, offering)

        await session.commit()

    log.info(
        "Seeded catalog entities: faculties=%d programs=%d levels=%d semesters=%d courses=%d offerings=%d",
        len(payload["faculties"]),
        len(payload["programs"]),
        len(payload["levels"]),
        len(payload["semesters"]),
        len(payload["courses"]),
        len(payload["offerings"]),
    )
    return 0


def main() -> int:
    setup_logging()
    return asyncio.run(async_main())


if __name__ == "__main__":
    raise SystemExit(main())
