from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request, status

from src.api.admin_auth import require_admin_permission
from src.domains.admin.catalog_service import AdminCatalogService
from src.domains.catalog.service import CatalogService


router = APIRouter(prefix="/admin/catalog", tags=["admin-catalog"])


def get_catalog_service() -> CatalogService:
    return CatalogService()


def get_admin_catalog_service(_request: Request) -> AdminCatalogService:
    return AdminCatalogService()


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


@router.get("/offerings")
async def list_offerings(
    request: Request,
    faculty_code: str | None = Query(default=None),
    program_code: str | None = Query(default=None),
    level_code: str | None = Query(default=None),
    semester_code: str | None = Query(default=None),
    _principal=Depends(require_admin_permission("catalog.view")),
):
    service = get_admin_catalog_service(request)
    items = await service.list_offerings(
        faculty_code=faculty_code,
        program_code=program_code,
        level_code=level_code,
        semester_code=semester_code,
    )
    return {"kind": "offerings", "items": items, "count": len(items)}


@router.post("/offerings", status_code=status.HTTP_201_CREATED)
async def upsert_offering(
    request: Request,
    principal=Depends(require_admin_permission("catalog.edit")),
):
    service = get_admin_catalog_service(request)
    payload = await request.json()
    return await service.upsert_offering(
        payload,
        actor_staff_user_id=principal.staff_user_id,
    )
