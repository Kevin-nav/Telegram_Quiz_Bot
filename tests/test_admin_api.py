import pytest

from types import SimpleNamespace

from tests.fakes import FakeRedis


class FakeAuthService:
    def __init__(self, principals):
        self.principals = principals

    async def get_principal(self, staff_user_id: int):
        return self.principals.get(staff_user_id)


class FakePermissionService:
    def __init__(self, permissions):
        self.permissions = permissions

    async def user_has_permission(self, staff_user_id: int, permission_code: str) -> bool:
        return permission_code in self.permissions.get(staff_user_id, set())


class FakeCatalogService:
    async def get_faculties(self):
        return [{"code": "engineering", "name": "Faculty of Engineering"}]

    async def get_programs(self, faculty_code: str):
        return [{"code": "mechanical-engineering", "name": "Mechanical Engineering"}]

    async def get_levels(self, program_code: str):
        return [{"code": "100", "name": "Level 100"}]

    async def get_semesters(self, program_code: str, level_code: str):
        return [{"code": "first", "name": "First Semester", "active": True}]

    async def get_courses(
        self,
        faculty_code: str,
        program_code: str,
        level_code: str,
        semester_code: str,
    ):
        return [
            {
                "code": "calculus",
                "name": "Calculus",
                "level_code": level_code,
                "semester_code": semester_code,
            }
        ]


@pytest.mark.asyncio
async def test_admin_auth_me_returns_current_principal(async_client, monkeypatch):
    import src.api.admin_auth as admin_auth

    monkeypatch.setattr(
        admin_auth,
        "get_auth_service",
        lambda request: FakeAuthService(
            {
                101: SimpleNamespace(
                    staff_user_id=101,
                    email="admin@example.com",
                    display_name="Admin User",
                )
            }
        ),
    )

    response = await async_client.get(
        "/admin/auth/me",
        headers={"X-Admin-User-Id": "101"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "staff_user_id": 101,
        "email": "admin@example.com",
        "display_name": "Admin User",
    }


@pytest.mark.asyncio
async def test_admin_catalog_allows_view_permission(async_client, monkeypatch):
    import src.api.admin_auth as admin_auth
    import src.api.admin_catalog as admin_catalog

    monkeypatch.setattr(
        admin_auth,
        "get_auth_service",
        lambda request: FakeAuthService(
            {
                101: SimpleNamespace(
                    staff_user_id=101,
                    email="admin@example.com",
                    display_name="Admin User",
                )
            }
        ),
    )
    monkeypatch.setattr(
        admin_auth,
        "get_permission_service",
        lambda request: FakePermissionService({101: {"catalog.view"}}),
    )
    monkeypatch.setattr(
        admin_catalog,
        "get_catalog_service",
        lambda: FakeCatalogService(),
    )

    response = await async_client.get(
        "/admin/catalog",
        headers={"X-Admin-User-Id": "101"},
    )

    assert response.status_code == 200
    assert response.json()["kind"] == "faculties"
    assert response.json()["items"][0]["code"] == "engineering"


@pytest.mark.asyncio
async def test_admin_questions_rejects_missing_permission(async_client, monkeypatch):
    import src.api.admin_auth as admin_auth

    monkeypatch.setattr(
        admin_auth,
        "get_auth_service",
        lambda request: FakeAuthService(
            {
                102: SimpleNamespace(
                    staff_user_id=102,
                    email="editor@example.com",
                    display_name="Editor User",
                )
            }
        ),
    )
    monkeypatch.setattr(
        admin_auth,
        "get_permission_service",
        lambda request: FakePermissionService({102: {"catalog.view"}}),
    )

    response = await async_client.get(
        "/admin/questions",
        headers={"X-Admin-User-Id": "102"},
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_staff_lookup_requires_permission(async_client, monkeypatch):
    import src.api.admin_auth as admin_auth

    monkeypatch.setattr(
        admin_auth,
        "get_auth_service",
        lambda request: FakeAuthService(
            {
                101: SimpleNamespace(
                    staff_user_id=101,
                    email="admin@example.com",
                    display_name="Admin User",
                ),
                202: SimpleNamespace(
                    staff_user_id=202,
                    email="staff@example.com",
                    display_name="Staff User",
                ),
            }
        ),
    )
    monkeypatch.setattr(
        admin_auth,
        "get_permission_service",
        lambda request: FakePermissionService({101: {"staff.view"}}),
    )

    response = await async_client.get(
        "/admin/staff/202",
        headers={"X-Admin-User-Id": "101"},
    )

    assert response.status_code == 200
    assert response.json()["staff_user_id"] == 202
    assert response.json()["requested_by"] == 101
