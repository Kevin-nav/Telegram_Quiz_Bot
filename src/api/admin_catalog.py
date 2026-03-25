from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from src.api.admin_auth import require_admin_permission
from src.domains.catalog.service import CatalogService


router = APIRouter(prefix="/admin/catalog", tags=["admin-catalog"])


def get_catalog_service() -> CatalogService:
    return CatalogService()


@router.get("")
async def read_catalog(
    faculty_code: str | None = Query(default=None),
    program_code: str | None = Query(default=None),
    level_code: str | None = Query(default=None),
    semester_code: str | None = Query(default=None),
    _principal=Depends(require_admin_permission("catalog.view")),
):
    catalog_service = get_catalog_service()
    if faculty_code and program_code and level_code and semester_code:
        items = await catalog_service.get_courses(
            faculty_code=faculty_code,
            program_code=program_code,
            level_code=level_code,
            semester_code=semester_code,
        )
        return {"kind": "courses", "items": items}

    if faculty_code and program_code and level_code:
        items = await catalog_service.get_semesters(
            program_code=program_code,
            level_code=level_code,
        )
        return {"kind": "semesters", "items": items}

    if faculty_code and program_code:
        items = await catalog_service.get_levels(program_code=program_code)
        return {"kind": "levels", "items": items}

    if faculty_code:
        items = await catalog_service.get_programs(faculty_code=faculty_code)
        return {"kind": "programs", "items": items}

    items = await catalog_service.get_faculties()
    return {"kind": "faculties", "items": items}
