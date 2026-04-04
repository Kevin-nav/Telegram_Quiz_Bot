from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from src.domains.admin.staff_service import AdminStaffService
from src.domains.admin.password_service import PasswordService


class FakeStaffRepo:
    def __init__(self, users=None, roles_by_user=None):
        self.users = {user.id: user for user in (users or [])}
        self.roles_by_user = {
            staff_user_id: list(role_codes)
            for staff_user_id, role_codes in (roles_by_user or {}).items()
        }
        self.next_id = max(self.users, default=0) + 1

    async def get_by_id(self, staff_user_id: int):
        return self.users.get(staff_user_id)

    async def get_by_email(self, email: str):
        for user in self.users.values():
            if user.email == email:
                return user
        return None

    async def create_staff_user(
        self,
        *,
        email,
        display_name=None,
        is_active=True,
        password_hash=None,
        must_change_password=True,
        last_selected_bot_id=None,
    ):
        user = SimpleNamespace(
            id=self.next_id,
            email=email,
            display_name=display_name,
            is_active=is_active,
            password_hash=password_hash,
            must_change_password=must_change_password,
            last_selected_bot_id=last_selected_bot_id,
            password_updated_at=None,
        )
        self.users[user.id] = user
        self.next_id += 1
        return user

    async def update_staff_user(self, staff_user_id: int, **updates):
        user = self.users.get(staff_user_id)
        if user is None:
            return None
        for key, value in updates.items():
            setattr(user, key, value)
        return user

    async def list_staff_users(self):
        return list(self.users.values())

    async def list_role_codes_for_user(self, staff_user_id: int):
        return list(self.roles_by_user.get(staff_user_id, []))

    async def replace_roles_for_user(self, staff_user_id: int, role_codes: list[str]):
        self.roles_by_user[staff_user_id] = list(role_codes)
        return self.roles_by_user[staff_user_id]

    async def update_password(self, staff_user_id: int, **updates):
        return await self.update_staff_user(staff_user_id, **updates)


class FakePermissionRepo:
    def __init__(self, permissions_by_user=None):
        self.permissions_by_user = {
            user_id: list(codes)
            for user_id, codes in (permissions_by_user or {}).items()
        }

    async def list_direct_permission_codes_for_user(self, staff_user_id: int):
        return list(self.permissions_by_user.get(staff_user_id, []))

    async def replace_direct_permissions_for_user(self, staff_user_id: int, permission_codes):
        self.permissions_by_user[staff_user_id] = list(permission_codes)
        return self.permissions_by_user[staff_user_id]


class FakeBotAccessRepo:
    def __init__(self, bot_access_by_user=None):
        self.bot_access_by_user = {
            user_id: list(bot_ids)
            for user_id, bot_ids in (bot_access_by_user or {}).items()
        }

    async def list_active_bot_ids_for_user(self, staff_user_id: int):
        return list(self.bot_access_by_user.get(staff_user_id, []))

    async def replace_bot_access_for_user(self, staff_user_id: int, bot_ids: list[str]):
        self.bot_access_by_user[staff_user_id] = list(bot_ids)
        return self.bot_access_by_user[staff_user_id]


class FakeCatalogAccessRepo:
    def __init__(self, catalog_access_by_user=None):
        self.catalog_access_by_user = {
            user_id: list(entries)
            for user_id, entries in (catalog_access_by_user or {}).items()
        }

    async def list_catalog_access_for_user(self, staff_user_id: int):
        return list(self.catalog_access_by_user.get(staff_user_id, []))

    async def replace_catalog_access_for_user(self, staff_user_id: int, entries):
        self.catalog_access_by_user[staff_user_id] = list(entries)
        return self.catalog_access_by_user[staff_user_id]


class FakeSessionRepo:
    def __init__(self):
        self.revoked_user_ids = []

    async def revoke_sessions_for_user(self, staff_user_id: int, *, revoked_at):
        assert revoked_at.tzinfo == UTC
        self.revoked_user_ids.append(staff_user_id)
        return 1


class FakeAuditRepo:
    def __init__(self):
        self.entries = []

    async def create_audit_log(self, **payload):
        self.entries.append(payload)


@pytest.mark.asyncio
async def test_create_non_super_admin_requires_exactly_one_bot_scope():
    service = AdminStaffService(
        staff_user_repository=FakeStaffRepo(),
        permission_repository=FakePermissionRepo(),
        staff_bot_access_repository=FakeBotAccessRepo(),
        staff_catalog_access_repository=FakeCatalogAccessRepo(),
        admin_session_repository=FakeSessionRepo(),
        password_service=PasswordService(),
        audit_log_repository=FakeAuditRepo(),
    )

    with pytest.raises(ValueError, match="exactly one bot workspace"):
        await service.create_staff_user(
            {
                "email": "editor@example.com",
                "display_name": "Editor",
                "role_codes": ["content_editor"],
                "permission_codes": ["questions.view"],
                "bot_access": ["adarkwa", "tanjah"],
                "temporary_password": "temp-password",
            }
        )


@pytest.mark.asyncio
async def test_create_super_admin_and_catalog_access_payload():
    service = AdminStaffService(
        staff_user_repository=FakeStaffRepo(),
        permission_repository=FakePermissionRepo(),
        staff_bot_access_repository=FakeBotAccessRepo(),
        staff_catalog_access_repository=FakeCatalogAccessRepo(),
        admin_session_repository=FakeSessionRepo(),
        password_service=PasswordService(),
        audit_log_repository=FakeAuditRepo(),
    )

    result = await service.create_staff_user(
        {
            "email": "admin@example.com",
            "display_name": "Admin User",
            "role_codes": ["super_admin"],
            "permission_codes": ["staff.view"],
            "bot_access": ["adarkwa", "tanjah"],
            "catalog_access": [
                {
                    "bot_id": "adarkwa",
                    "program_code": "mechanical-engineering",
                    "level_code": "100",
                    "course_code": "calculus",
                }
            ],
            "temporary_password": "temp-password",
        },
        actor_staff_user_id=999,
    )

    assert result["staff_user_id"] == 1
    assert result["must_change_password"] is True
    assert result["bot_access"] == ["adarkwa", "tanjah"]
    assert result["catalog_access"] == [
        {
            "bot_id": "adarkwa",
            "program_code": "mechanical-engineering",
            "level_code": "100",
            "course_code": "calculus",
        }
    ]


@pytest.mark.asyncio
async def test_reset_staff_password_sets_temporary_password_and_revokes_sessions():
    password_service = PasswordService()
    staff_repo = FakeStaffRepo(
        users=[
            SimpleNamespace(
                id=7,
                email="editor@example.com",
                display_name="Editor",
                is_active=True,
                must_change_password=False,
                password_hash=password_service.hash_password("old-password"),
                last_selected_bot_id="adarkwa",
            )
        ],
        roles_by_user={7: ["content_editor"]},
    )
    bot_repo = FakeBotAccessRepo({7: ["adarkwa"]})
    catalog_repo = FakeCatalogAccessRepo({7: []})
    session_repo = FakeSessionRepo()
    audit_repo = FakeAuditRepo()
    service = AdminStaffService(
        staff_user_repository=staff_repo,
        permission_repository=FakePermissionRepo({7: ["questions.view"]}),
        staff_bot_access_repository=bot_repo,
        staff_catalog_access_repository=catalog_repo,
        admin_session_repository=session_repo,
        password_service=password_service,
        audit_log_repository=audit_repo,
    )

    result = await service.reset_staff_password(
        7,
        "new-temp-password",
        actor_staff_user_id=1,
    )

    assert result is not None
    assert result["must_change_password"] is True
    assert password_service.verify_password(
        "new-temp-password",
        staff_repo.users[7].password_hash,
    )
    assert session_repo.revoked_user_ids == [7]
    assert audit_repo.entries[-1]["action"] == "staff.password_reset"
