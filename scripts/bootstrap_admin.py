from __future__ import annotations

import argparse
import asyncio
import logging
import secrets
import sys
from pathlib import Path

from sqlalchemy import delete, select

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.domains.admin.staff_service import AdminStaffService
from src.infra.db.models.permission import Permission
from src.infra.db.models.staff_role import StaffRole
from src.infra.db.models.staff_role_permission import StaffRolePermission
from src.infra.db.session import AsyncSessionLocal


log = logging.getLogger(__name__)

DEFAULT_PERMISSIONS = [
    ("analytics.view", "View analytics"),
    ("analytics.export", "Export analytics"),
    ("audit.view", "View audit log"),
    ("catalog.view", "View catalog"),
    ("catalog.edit", "Edit catalog"),
    ("questions.view", "View question bank"),
    ("questions.edit", "Edit questions"),
    ("questions.publish", "Publish questions"),
    ("staff.view", "View staff"),
    ("staff.create", "Create staff"),
    ("staff.edit_permissions", "Edit permissions"),
]

DEFAULT_ROLES = [
    (
        "super_admin",
        "Super admin",
        "Full access across staff, catalog, content, and audit actions.",
        [code for code, _name in DEFAULT_PERMISSIONS],
    ),
    (
        "content_editor",
        "Content editor",
        "Can revise questions and explanations, then queue them for review.",
        ["questions.view", "questions.edit", "questions.publish", "audit.view"],
    ),
    (
        "catalog_manager",
        "Catalog manager",
        "Can maintain faculties, programs, levels, semesters, courses, and offerings.",
        ["catalog.view", "catalog.edit", "audit.view"],
    ),
    (
        "analytics_viewer",
        "Analytics viewer",
        "Can inspect dashboards and performance trends without editing.",
        ["analytics.view", "audit.view"],
    ),
]

DEFAULT_ADMIN_BOTS = ("adarkwa", "tanjah")


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-7s  %(name)s  %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stderr,
    )


async def ensure_permissions_and_roles() -> None:
    async with AsyncSessionLocal() as session:
        permission_map: dict[str, Permission] = {}

        for code, name in DEFAULT_PERMISSIONS:
            permission = await session.scalar(
                select(Permission).where(Permission.code == code)
            )
            if permission is None:
                permission = Permission(code=code, name=name, description=None)
                session.add(permission)
                await session.flush()
            else:
                permission.name = name
            permission_map[code] = permission

        role_map: dict[str, StaffRole] = {}
        for code, name, description, _permission_codes in DEFAULT_ROLES:
            role = await session.scalar(select(StaffRole).where(StaffRole.code == code))
            if role is None:
                role = StaffRole(code=code, name=name, description=description)
                session.add(role)
                await session.flush()
            else:
                role.name = name
                role.description = description
            role_map[code] = role

        for code, _name, _description, permission_codes in DEFAULT_ROLES:
            role = role_map[code]
            await session.execute(
                delete(StaffRolePermission).where(
                    StaffRolePermission.staff_role_id == role.id
                )
            )
            session.add_all(
                [
                    StaffRolePermission(
                        staff_role_id=role.id,
                        permission_id=permission_map[permission_code].id,
                    )
                    for permission_code in permission_codes
                    if permission_code in permission_map
                ]
            )

        await session.commit()


async def bootstrap_admin(
    email: str,
    display_name: str | None,
    temporary_password: str,
    bot_access: tuple[str, ...] = DEFAULT_ADMIN_BOTS,
) -> dict:
    await ensure_permissions_and_roles()
    service = AdminStaffService()
    return await service.create_staff_user(
        {
            "email": email,
            "display_name": display_name,
            "is_active": True,
            "role_codes": ["super_admin"],
            "permission_codes": [],
            "temporary_password": temporary_password,
            "bot_access": list(bot_access),
            "catalog_access": [],
        }
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Bootstrap a first super-admin staff user for the admin frontend."
    )
    parser.add_argument("--email", required=True, help="Admin email address.")
    parser.add_argument(
        "--display-name",
        default="Admin User",
        help="Human-friendly display name.",
    )
    parser.add_argument(
        "--temporary-password",
        default=None,
        help="Temporary password for the first login. If omitted, one is generated.",
    )
    parser.add_argument(
        "--bot-access",
        nargs="+",
        default=list(DEFAULT_ADMIN_BOTS),
        choices=list(DEFAULT_ADMIN_BOTS),
        help="Bot workspaces to grant to the first super-admin.",
    )
    return parser


async def async_main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    temporary_password = args.temporary_password or secrets.token_urlsafe(12)
    payload = await bootstrap_admin(
        args.email,
        args.display_name,
        temporary_password,
        tuple(args.bot_access),
    )
    log.info(
        "Admin ready: staff_user_id=%s email=%s roles=%s bot_access=%s temporary_password=%s",
        payload.get("staff_user_id"),
        payload.get("email"),
        payload.get("role_codes"),
        payload.get("bot_access"),
        temporary_password,
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    setup_logging()
    return asyncio.run(async_main(argv))


if __name__ == "__main__":
    raise SystemExit(main())
