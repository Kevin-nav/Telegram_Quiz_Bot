from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request, status

from src.api.admin_auth import (
    get_permission_service,
    require_admin_permission,
)
from src.core.config import settings
from src.domains.admin.auth_service import AdminPrincipal
from src.domains.admin.catalog_service import AdminCatalogService
from src.domains.catalog.service import CatalogService


router = APIRouter(prefix="/admin/catalog", tags=["admin-catalog"])


def get_catalog_service(principal: AdminPrincipal | None = None) -> CatalogService:
    bot_id = getattr(principal, "active_bot_id", None) if principal else None
    bot_config = settings.bot_configs.get(bot_id) if bot_id else None
    if bot_config is None:
        return CatalogService()

    return CatalogService(
        allowed_course_codes=bot_config.allowed_course_codes,
        fixed_faculty_code=bot_config.fixed_faculty_code,
        fixed_level_code=bot_config.fixed_level_code,
    )


def get_admin_catalog_service(_request: Request) -> AdminCatalogService:
    return AdminCatalogService()


@router.get("")
async def read_catalog(
    request: Request,
    faculty_code: str | None = Query(default=None),
    program_code: str | None = Query(default=None),
    level_code: str | None = Query(default=None),
    semester_code: str | None = Query(default=None),
    principal: AdminPrincipal = Depends(require_admin_permission("catalog.view")),
):
    catalog_service = (
        get_catalog_service(principal)
        if getattr(principal, "active_bot_id", None)
        else get_catalog_service()
    )
    if faculty_code and program_code and level_code and semester_code:
        items = await catalog_service.get_courses(
            faculty_code=faculty_code,
            program_code=program_code,
            level_code=level_code,
            semester_code=semester_code,
        )
        return {
            "kind": "courses",
            "items": await _filter_catalog_items_for_principal(
                request,
                principal,
                items,
                program_code=program_code,
                level_code=level_code,
            ),
        }

    if faculty_code and program_code and level_code:
        items = await catalog_service.get_semesters(
            program_code=program_code,
            level_code=level_code,
        )
        return {
            "kind": "semesters",
            "items": await _filter_catalog_items_for_principal(
                request,
                principal,
                items,
                program_code=program_code,
                level_code=level_code,
            ),
        }

    if faculty_code and program_code:
        items = await catalog_service.get_levels(program_code=program_code)
        return {
            "kind": "levels",
            "items": await _filter_catalog_items_for_principal(
                request,
                principal,
                items,
                program_code=program_code,
            ),
        }

    if faculty_code:
        items = await catalog_service.get_programs(faculty_code=faculty_code)
        return {
            "kind": "programs",
            "items": await _filter_catalog_items_for_principal(
                request,
                principal,
                items,
            ),
        }

    items = await catalog_service.get_faculties()
    return {"kind": "faculties", "items": items}


@router.get("/offerings")
async def list_offerings(
    request: Request,
    faculty_code: str | None = Query(default=None),
    program_code: str | None = Query(default=None),
    level_code: str | None = Query(default=None),
    semester_code: str | None = Query(default=None),
    principal: AdminPrincipal = Depends(require_admin_permission("catalog.view")),
):
    service = get_admin_catalog_service(request)
    items = await service.list_offerings(
        faculty_code=faculty_code,
        program_code=program_code,
        level_code=level_code,
        semester_code=semester_code,
    )
    items = await _filter_catalog_items_for_principal(
        request,
        principal,
        items,
        program_code=program_code,
        level_code=level_code,
    )
    return {"kind": "offerings", "items": items, "count": len(items)}


@router.post("/offerings", status_code=status.HTTP_201_CREATED)
async def upsert_offering(
    request: Request,
    principal: AdminPrincipal = Depends(require_admin_permission("catalog.edit")),
):
    service = get_admin_catalog_service(request)
    payload = await request.json()
    await _require_catalog_access(
        request,
        principal,
        program_code=str(payload.get("program_code") or "").strip() or None,
        level_code=str(payload.get("level_code") or "").strip() or None,
        course_code=str(payload.get("course_code") or "").strip() or None,
    )
    return await service.upsert_offering(
        payload,
        actor_staff_user_id=principal.staff_user_id,
    )


async def _filter_catalog_items_for_principal(
    request: Request,
    principal: AdminPrincipal,
    items: list[dict],
    *,
    program_code: str | None = None,
    level_code: str | None = None,
) -> list[dict]:
    bot_id = getattr(principal, "active_bot_id", None)
    if not bot_id:
        return items

    permission_service = get_permission_service(request)
    visible_items = []
    for item in items:
        item_program_code = item.get("program_code") or program_code
        item_level_code = item.get("level_code") or level_code
        item_course_code = item.get("course_code")
        if item_course_code is None and "semester_code" in item:
            item_course_code = item.get("code")
        if await permission_service.user_can_access_bot_catalog_scope(
            principal.staff_user_id,
            bot_id,
            program_code=item_program_code,
            level_code=item_level_code,
            course_code=item_course_code,
        ):
            visible_items.append(item)
    return visible_items


async def _require_catalog_access(
    request: Request,
    principal: AdminPrincipal,
    *,
    program_code: str | None = None,
    level_code: str | None = None,
    course_code: str | None = None,
) -> None:
    bot_id = getattr(principal, "active_bot_id", None)
    if not bot_id:
        return

    permission_service = get_permission_service(request)
    allowed = await permission_service.user_can_access_bot_catalog_scope(
        principal.staff_user_id,
        bot_id,
        program_code=program_code,
        level_code=level_code,
        course_code=course_code,
    )
    if not allowed:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This admin user cannot access the requested catalog scope.",
        )
