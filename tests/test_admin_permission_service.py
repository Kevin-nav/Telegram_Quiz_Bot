import pytest

from src.domains.admin.permission_service import PermissionService


class FakeStaffUser:
    def __init__(self, user_id: int, is_active: bool = True):
        self.id = user_id
        self.email = f"user-{user_id}@example.com"
        self.display_name = f"User {user_id}"
        self.is_active = is_active


class FakeStaffUserRepository:
    def __init__(self, users: dict[int, FakeStaffUser]):
        self.users = users

    async def get_by_id(self, staff_user_id: int):
        return self.users.get(staff_user_id)


class FakePermissionRepository:
    def __init__(self, direct: dict[int, list[str]], role_based: dict[int, list[str]]):
        self.direct = direct
        self.role_based = role_based

    async def list_effective_permission_codes_for_user(self, staff_user_id: int) -> list[str]:
        return sorted(
            set(self.direct.get(staff_user_id, []))
            | set(self.role_based.get(staff_user_id, []))
        )


@pytest.mark.asyncio
async def test_user_has_permission_allows_direct_grants():
    service = PermissionService(
        staff_user_repository=FakeStaffUserRepository({1: FakeStaffUser(1)}),
        permission_repository=FakePermissionRepository({1: ["catalog.view"]}, {}),
    )

    assert await service.user_has_permission(1, "catalog.view") is True


@pytest.mark.asyncio
async def test_user_has_permission_allows_role_grants():
    service = PermissionService(
        staff_user_repository=FakeStaffUserRepository({1: FakeStaffUser(1)}),
        permission_repository=FakePermissionRepository({}, {1: ["questions.edit"]}),
    )

    assert await service.user_has_permission(1, "questions.edit") is True


@pytest.mark.asyncio
async def test_user_has_permission_denies_missing_permission():
    service = PermissionService(
        staff_user_repository=FakeStaffUserRepository({1: FakeStaffUser(1)}),
        permission_repository=FakePermissionRepository({}, {}),
    )

    assert await service.user_has_permission(1, "audit.view") is False


@pytest.mark.asyncio
async def test_user_has_permission_denies_inactive_user():
    service = PermissionService(
        staff_user_repository=FakeStaffUserRepository({1: FakeStaffUser(1, is_active=False)}),
        permission_repository=FakePermissionRepository({1: ["catalog.view"]}, {1: ["questions.edit"]}),
    )

    assert await service.user_has_permission(1, "catalog.view") is False
