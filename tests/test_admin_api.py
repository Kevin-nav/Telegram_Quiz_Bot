import pytest

from datetime import datetime, timezone
from types import SimpleNamespace

from src.domains.admin.audit_service import AdminAuditService
from src.domains.admin.catalog_service import AdminCatalogService
from src.domains.admin.question_service import AdminQuestionService
from src.domains.admin.staff_service import AdminStaffService


class FakeAuthService:
    def __init__(
        self,
        principals=None,
        principals_by_session_token=None,
        login_result=None,
        set_password_result=None,
        select_bot_result=None,
    ):
        self.principals = principals or {}
        self.principals_by_session_token = principals_by_session_token or {}
        self.login_result = login_result
        self.set_password_result = set_password_result
        self.select_bot_result = select_bot_result
        self.logged_out_tokens = []

    async def get_principal(self, staff_user_id: int):
        return self.principals.get(staff_user_id)

    async def get_principal_for_session_token(self, session_token: str):
        return self.principals_by_session_token.get(session_token)

    async def login(self, *_args, **_kwargs):
        return self.login_result

    async def logout(self, session_token: str):
        self.logged_out_tokens.append(session_token)

    async def set_password(self, *_args, **_kwargs):
        return self.set_password_result

    async def set_active_bot(self, *_args, **_kwargs):
        return self.select_bot_result


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


class FakeStaffRepo:
    def __init__(self, users=None, roles_by_user=None):
        self.users = {user.id: user for user in (users or [])}
        self.roles_by_user = {
            staff_user_id: list(role_codes)
            for staff_user_id, role_codes in (roles_by_user or {}).items()
        }
        self.next_id = (max(self.users) + 1) if self.users else 1

    async def get_by_id(self, staff_user_id: int):
        return self.users.get(staff_user_id)

    async def get_by_email(self, email: str):
        for user in self.users.values():
            if user.email == email:
                return user
        return None

    async def list_staff_users(self):
        return sorted(self.users.values(), key=lambda user: user.email)

    async def create_staff_user(
        self,
        *,
        email: str,
        display_name: str | None = None,
        is_active: bool = True,
        password_hash: str | None = None,
        must_change_password: bool = True,
        last_selected_bot_id: str | None = None,
    ):
        user = SimpleNamespace(
            id=self.next_id,
            email=email,
            display_name=display_name,
            is_active=is_active,
            password_hash=password_hash,
            must_change_password=must_change_password,
            last_selected_bot_id=last_selected_bot_id,
        )
        self.users[user.id] = user
        self.next_id += 1
        return user

    async def update_staff_user(self, staff_user_id: int, **updates):
        user = self.users.get(staff_user_id)
        if user is None:
            return None

        for field in (
            "email",
            "display_name",
            "is_active",
            "password_hash",
            "must_change_password",
            "last_selected_bot_id",
        ):
            if field in updates and updates[field] is not None:
                setattr(user, field, updates[field])
        return user

    async def list_role_codes_for_user(self, staff_user_id: int):
        return list(self.roles_by_user.get(staff_user_id, []))

    async def replace_roles_for_user(self, staff_user_id: int, role_codes: list[str]):
        self.roles_by_user[staff_user_id] = list(dict.fromkeys(role_codes))
        return self.roles_by_user[staff_user_id]


class FakePermissionRepo:
    def __init__(self, permissions_by_user=None):
        self.permissions_by_user = {
            staff_user_id: list(permission_codes)
            for staff_user_id, permission_codes in (permissions_by_user or {}).items()
        }

    async def list_direct_permission_codes_for_user(self, staff_user_id: int):
        return list(self.permissions_by_user.get(staff_user_id, []))

    async def replace_direct_permissions_for_user(
        self, staff_user_id: int, permission_codes
    ):
        self.permissions_by_user[staff_user_id] = list(dict.fromkeys(permission_codes))
        return self.permissions_by_user[staff_user_id]


class FakeBotAccessRepo:
    def __init__(self, bot_access_by_user=None):
        self.bot_access_by_user = {
            staff_user_id: list(bot_ids)
            for staff_user_id, bot_ids in (bot_access_by_user or {}).items()
        }

    async def list_active_bot_ids_for_user(self, staff_user_id: int):
        return list(self.bot_access_by_user.get(staff_user_id, []))

    async def replace_bot_access_for_user(self, staff_user_id: int, bot_ids: list[str]):
        self.bot_access_by_user[staff_user_id] = list(bot_ids)
        return self.bot_access_by_user[staff_user_id]


class FakeCatalogAccessRepo:
    def __init__(self, catalog_access_by_user=None):
        self.catalog_access_by_user = {
            staff_user_id: list(entries)
            for staff_user_id, entries in (catalog_access_by_user or {}).items()
        }

    async def list_catalog_access_for_user(self, staff_user_id: int):
        return list(self.catalog_access_by_user.get(staff_user_id, []))

    async def replace_catalog_access_for_user(self, staff_user_id: int, entries):
        self.catalog_access_by_user[staff_user_id] = list(entries)
        return self.catalog_access_by_user[staff_user_id]


class FakeAuditRepo:
    def __init__(self, entries=None):
        self.entries = list(entries or [])
        self.created_entries = []

    async def create_audit_log(self, **kwargs):
        entry = SimpleNamespace(
            id=len(self.entries) + len(self.created_entries) + 1,
            created_at=datetime(2026, 3, 25, tzinfo=timezone.utc),
            **kwargs,
        )
        self.created_entries.append(entry)
        return entry

    async def list_audit_logs(self, *, limit: int = 100, offset: int = 0):
        pool = self.entries + self.created_entries
        return pool[offset : offset + limit]


class FakeCatalogRepo:
    def __init__(self, offerings=None):
        self.offerings = {}
        next_id = 1
        for item in offerings or []:
            offering = SimpleNamespace(
                id=item.get("id", next_id),
                program_code=item["program_code"],
                level_code=item["level_code"],
                semester_code=item["semester_code"],
                course_code=item["course_code"],
                is_active=item.get("is_active", True),
            )
            key = (
                offering.program_code,
                offering.level_code,
                offering.semester_code,
                offering.course_code,
            )
            self.offerings[key] = offering
            next_id = max(next_id, offering.id + 1)
        self.next_id = next_id

    async def list_offerings(self, **filters):
        items = list(self.offerings.values())
        for field, value in filters.items():
            if value is not None:
                items = [item for item in items if getattr(item, field) == value]
        return items

    async def upsert_offering(self, payload: dict):
        key = (
            payload["program_code"],
            payload["level_code"],
            payload["semester_code"],
            payload["course_code"],
        )
        offering = self.offerings.get(key)
        if offering is None:
            offering = SimpleNamespace(
                id=self.next_id,
                program_code=payload["program_code"],
                level_code=payload["level_code"],
                semester_code=payload["semester_code"],
                course_code=payload["course_code"],
                is_active=payload.get("is_active", True),
            )
            self.offerings[key] = offering
            self.next_id += 1
        else:
            offering.is_active = payload.get("is_active", offering.is_active)
        return offering


class FakeCatalogStateStore:
    def __init__(self):
        self.invalidate_catalog_cache_calls = 0

    async def invalidate_catalog_cache(self):
        self.invalidate_catalog_cache_calls += 1


class FakeQuestionRepo:
    def __init__(self, questions=None):
        self.questions = {
            question.question_key: question
            for question in (questions or [])
        }

    async def get_question(self, question_key: str):
        return self.questions.get(question_key)

    async def list_questions(self, *, course_id=None, status=None, limit=100, offset=0):
        items = list(self.questions.values())
        if course_id is not None:
            items = [question for question in items if question.course_id == course_id]
        if status is not None:
            items = [question for question in items if question.status == status]
        return items[offset : offset + limit]

    async def update_question(self, question_key: str, updates: dict):
        question = self.questions.get(question_key)
        if question is None:
            return None
        for key, value in updates.items():
            if value is not None:
                setattr(question, key, value)
        return question


@pytest.mark.asyncio
async def test_admin_auth_me_returns_current_principal(async_client, monkeypatch):
    import src.api.admin_auth as admin_auth

    monkeypatch.setattr(
        admin_auth,
        "get_auth_service",
        lambda request: FakeAuthService(
            principals_by_session_token={
                "session-101": SimpleNamespace(
                    staff_user_id=101,
                    email="admin@example.com",
                    display_name="Admin User",
                    role_codes=["super_admin"],
                    permission_codes=["staff.view"],
                    bot_access=["adarkwa", "tanjah"],
                    active_bot_id="adarkwa",
                    must_change_password=False,
                )
            },
        ),
    )

    response = await async_client.get(
        "/admin/auth/me",
        cookies={"admin_session": "session-101"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "staff_user_id": 101,
        "email": "admin@example.com",
        "display_name": "Admin User",
        "role_codes": ["super_admin"],
        "permission_codes": ["staff.view"],
        "bot_access": ["adarkwa", "tanjah"],
        "active_bot_id": "adarkwa",
        "must_change_password": False,
    }


@pytest.mark.asyncio
async def test_admin_auth_login_sets_session_cookie(async_client, monkeypatch):
    import src.api.admin_auth as admin_auth

    monkeypatch.setattr(
        admin_auth,
        "get_auth_service",
        lambda request: FakeAuthService(
            login_result=(
                SimpleNamespace(
                    staff_user_id=101,
                    email="admin@example.com",
                    display_name="Admin User",
                    role_codes=["super_admin"],
                    permission_codes=["staff.view"],
                    bot_access=["adarkwa", "tanjah"],
                    active_bot_id="adarkwa",
                    must_change_password=True,
                ),
                "issued-session-token",
            )
        ),
    )

    response = await async_client.post(
        "/admin/auth/login",
        json={"email": "admin@example.com", "password": "temp-password"},
    )

    assert response.status_code == 200
    assert response.json()["must_change_password"] is True
    assert response.cookies.get("admin_session") == "issued-session-token"


@pytest.mark.asyncio
async def test_admin_auth_set_password_uses_session_cookie(async_client, monkeypatch):
    import src.api.admin_auth as admin_auth

    monkeypatch.setattr(
        admin_auth,
        "get_auth_service",
        lambda request: FakeAuthService(
            principals_by_session_token={
                "session-101": SimpleNamespace(
                    staff_user_id=101,
                    email="admin@example.com",
                    display_name="Admin User",
                    role_codes=["super_admin"],
                    permission_codes=["staff.view"],
                    bot_access=["adarkwa", "tanjah"],
                    active_bot_id="adarkwa",
                    must_change_password=True,
                )
            },
            set_password_result=SimpleNamespace(
                staff_user_id=101,
                email="admin@example.com",
                display_name="Admin User",
                role_codes=["super_admin"],
                permission_codes=["staff.view"],
                bot_access=["adarkwa", "tanjah"],
                active_bot_id="adarkwa",
                must_change_password=False,
            ),
        ),
    )

    response = await async_client.post(
        "/admin/auth/set-password",
        cookies={"admin_session": "session-101"},
        json={
            "current_password": "temp-password",
            "new_password": "new-password-123",
        },
    )

    assert response.status_code == 200
    assert response.json()["must_change_password"] is False


@pytest.mark.asyncio
async def test_admin_auth_logout_clears_session_cookie(async_client, monkeypatch):
    import src.api.admin_auth as admin_auth

    fake_auth_service = FakeAuthService(
        principals_by_session_token={
            "session-101": SimpleNamespace(
                staff_user_id=101,
                email="admin@example.com",
                display_name="Admin User",
                role_codes=["super_admin"],
                permission_codes=["staff.view"],
                bot_access=["adarkwa", "tanjah"],
                active_bot_id="adarkwa",
                must_change_password=False,
            )
        }
    )
    monkeypatch.setattr(
        admin_auth,
        "get_auth_service",
        lambda request: fake_auth_service,
    )

    response = await async_client.post(
        "/admin/auth/logout",
        cookies={"admin_session": "session-101"},
    )

    assert response.status_code == 204
    assert fake_auth_service.logged_out_tokens == ["session-101"]


@pytest.mark.asyncio
async def test_admin_staff_list_and_update_permissions(async_client, monkeypatch):
    import src.api.admin_auth as admin_auth
    import src.api.admin_staff as admin_staff

    fake_staff_repo = FakeStaffRepo(
        users=[
            SimpleNamespace(
                id=202,
                email="staff@example.com",
                display_name="Staff User",
                is_active=True,
            )
        ],
        roles_by_user={202: ["content_editor"]},
    )
    fake_permission_repo = FakePermissionRepo({202: ["questions.view"]})
    fake_bot_access_repo = FakeBotAccessRepo({202: ["adarkwa"]})
    fake_catalog_access_repo = FakeCatalogAccessRepo({202: []})
    fake_audit_repo = FakeAuditRepo()
    staff_service = AdminStaffService(
        staff_user_repository=fake_staff_repo,
        permission_repository=fake_permission_repo,
        staff_bot_access_repository=fake_bot_access_repo,
        staff_catalog_access_repository=fake_catalog_access_repo,
        audit_log_repository=fake_audit_repo,
    )

    monkeypatch.setattr(
        admin_auth,
        "get_auth_service",
        lambda request: FakeAuthService(
            principals_by_session_token={
                "session-101": SimpleNamespace(
                    staff_user_id=101,
                    email="admin@example.com",
                    display_name="Admin User",
                )
            },
        ),
    )
    monkeypatch.setattr(
        admin_auth,
        "get_permission_service",
        lambda request: FakePermissionService({101: {"staff.view", "staff.create", "staff.edit_permissions"}}),
    )
    monkeypatch.setattr(admin_staff, "get_admin_staff_service", lambda request: staff_service)

    list_response = await async_client.get(
        "/admin/staff",
        cookies={"admin_session": "session-101"},
    )
    assert list_response.status_code == 200
    assert list_response.json()["count"] == 1
    assert list_response.json()["items"][0]["email"] == "staff@example.com"

    create_response = await async_client.post(
        "/admin/staff",
        cookies={"admin_session": "session-101"},
        json={
            "email": "new-admin@example.com",
            "display_name": "New Admin",
            "role_codes": ["super_admin"],
            "permission_codes": ["catalog.view", "questions.edit"],
            "bot_access": ["adarkwa", "tanjah"],
            "temporary_password": "temp-password",
        },
    )
    assert create_response.status_code == 201
    assert create_response.json()["email"] == "new-admin@example.com"
    assert create_response.json()["permission_codes"] == ["catalog.view", "questions.edit"]

    update_response = await async_client.patch(
        "/admin/staff/202",
        cookies={"admin_session": "session-101"},
        json={
            "permission_codes": ["catalog.view", "audit.view"],
            "role_codes": ["super_admin"],
            "bot_access": ["adarkwa", "tanjah"],
            "is_active": False,
        },
    )
    assert update_response.status_code == 200
    assert update_response.json()["is_active"] is False
    assert update_response.json()["role_codes"] == ["super_admin"]
    assert update_response.json()["permission_codes"] == ["catalog.view", "audit.view"]


@pytest.mark.asyncio
async def test_admin_catalog_write_invalidates_cache(async_client, monkeypatch):
    import src.api.admin_auth as admin_auth
    import src.api.admin_catalog as admin_catalog

    fake_catalog_repo = FakeCatalogRepo()
    fake_state_store = FakeCatalogStateStore()
    fake_audit_repo = FakeAuditRepo()
    catalog_service = AdminCatalogService(
        catalog_repository=fake_catalog_repo,
        state_store=fake_state_store,
        audit_log_repository=fake_audit_repo,
    )

    monkeypatch.setattr(
        admin_auth,
        "get_auth_service",
        lambda request: FakeAuthService(
            principals_by_session_token={
                "session-101": SimpleNamespace(
                    staff_user_id=101,
                    email="admin@example.com",
                    display_name="Admin User",
                )
            },
        ),
    )
    monkeypatch.setattr(
        admin_auth,
        "get_permission_service",
        lambda request: FakePermissionService({101: {"catalog.view", "catalog.edit"}}),
    )
    monkeypatch.setattr(
        admin_catalog,
        "get_admin_catalog_service",
        lambda request: catalog_service,
    )

    response = await async_client.post(
        "/admin/catalog/offerings",
        cookies={"admin_session": "session-101"},
        json={
            "program_code": "mechanical-engineering",
            "level_code": "100",
            "semester_code": "first",
            "course_code": "calculus",
            "is_active": True,
        },
    )

    assert response.status_code == 201
    assert response.json()["course_code"] == "calculus"
    assert fake_state_store.invalidate_catalog_cache_calls == 1
    assert fake_audit_repo.created_entries[0].action == "catalog.offering.updated"


@pytest.mark.asyncio
async def test_admin_questions_update_creates_audit_log(async_client, monkeypatch):
    import src.api.admin_auth as admin_auth
    import src.api.admin_questions as admin_questions

    fake_question_repo = FakeQuestionRepo(
        questions=[
            SimpleNamespace(
                question_key="q-1",
                course_id="calculus",
                course_slug="calculus",
                question_text="Original text",
                correct_option_text="A",
                short_explanation="Original explanation",
                status="draft",
                scaled_score=1.5,
                band=1,
            )
        ]
    )
    fake_audit_repo = FakeAuditRepo()
    question_service = AdminQuestionService(
        question_repository=fake_question_repo,
        audit_log_repository=fake_audit_repo,
    )

    monkeypatch.setattr(
        admin_auth,
        "get_auth_service",
        lambda request: FakeAuthService(
            principals_by_session_token={
                "session-101": SimpleNamespace(
                    staff_user_id=101,
                    email="editor@example.com",
                    display_name="Editor User",
                )
            },
        ),
    )
    monkeypatch.setattr(
        admin_auth,
        "get_permission_service",
        lambda request: FakePermissionService({101: {"questions.view", "questions.edit"}}),
    )
    monkeypatch.setattr(
        admin_questions,
        "get_admin_question_service",
        lambda request: question_service,
    )

    response = await async_client.patch(
        "/admin/questions/q-1",
        cookies={"admin_session": "session-101"},
        json={
            "question_text": "Updated text",
            "correct_option_text": "B",
            "short_explanation": "Updated explanation",
            "status": "ready",
        },
    )

    assert response.status_code == 200
    assert response.json()["question_text"] == "Updated text"
    assert fake_audit_repo.created_entries[0].action == "question.updated"
    assert fake_audit_repo.created_entries[0].after_data["status"] == "ready"


@pytest.mark.asyncio
async def test_admin_audit_listing_returns_entries(async_client, monkeypatch):
    import src.api.admin_auth as admin_auth
    import src.api.admin_audit as admin_audit

    fake_audit_repo = FakeAuditRepo(
        entries=[
            SimpleNamespace(
                id=1,
                actor_staff_user_id=101,
                action="question.updated",
                entity_type="question_bank",
                entity_id="q-1",
                before_data={"question_text": "Original"},
                after_data={"question_text": "Updated"},
                created_at=datetime(2026, 3, 25, tzinfo=timezone.utc),
            )
        ]
    )
    audit_service = AdminAuditService(audit_log_repository=fake_audit_repo)

    monkeypatch.setattr(
        admin_auth,
        "get_auth_service",
        lambda request: FakeAuthService(
            principals_by_session_token={
                "session-101": SimpleNamespace(
                    staff_user_id=101,
                    email="admin@example.com",
                    display_name="Admin User",
                )
            },
        ),
    )
    monkeypatch.setattr(
        admin_auth,
        "get_permission_service",
        lambda request: FakePermissionService({101: {"audit.view"}}),
    )
    monkeypatch.setattr(
        admin_audit,
        "get_admin_audit_service",
        lambda request: audit_service,
    )

    response = await async_client.get(
        "/admin/audit",
        cookies={"admin_session": "session-101"},
    )

    assert response.status_code == 200
    assert response.json()["count"] == 1
    assert response.json()["items"][0]["action"] == "question.updated"


@pytest.mark.asyncio
async def test_admin_catalog_allows_view_permission(async_client, monkeypatch):
    import src.api.admin_auth as admin_auth
    import src.api.admin_catalog as admin_catalog

    monkeypatch.setattr(
        admin_auth,
        "get_auth_service",
        lambda request: FakeAuthService(
            principals_by_session_token={
                "session-101": SimpleNamespace(
                    staff_user_id=101,
                    email="admin@example.com",
                    display_name="Admin User",
                )
            },
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
        cookies={"admin_session": "session-101"},
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
            principals_by_session_token={
                "session-102": SimpleNamespace(
                    staff_user_id=102,
                    email="editor@example.com",
                    display_name="Editor User",
                )
            },
        ),
    )
    monkeypatch.setattr(
        admin_auth,
        "get_permission_service",
        lambda request: FakePermissionService({102: {"catalog.view"}}),
    )

    response = await async_client.get(
        "/admin/questions",
        cookies={"admin_session": "session-102"},
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_staff_lookup_requires_permission(async_client, monkeypatch):
    import src.api.admin_auth as admin_auth
    import src.api.admin_staff as admin_staff

    fake_staff_repo = FakeStaffRepo(
        users=[
            SimpleNamespace(
                id=202,
                email="staff@example.com",
                display_name="Staff User",
                is_active=True,
            )
        ],
    )
    fake_permission_repo = FakePermissionRepo()
    fake_bot_access_repo = FakeBotAccessRepo({202: ["adarkwa"]})
    fake_catalog_access_repo = FakeCatalogAccessRepo({202: []})
    fake_audit_repo = FakeAuditRepo()
    staff_service = AdminStaffService(
        staff_user_repository=fake_staff_repo,
        permission_repository=fake_permission_repo,
        staff_bot_access_repository=fake_bot_access_repo,
        staff_catalog_access_repository=fake_catalog_access_repo,
        audit_log_repository=fake_audit_repo,
    )

    monkeypatch.setattr(
        admin_auth,
        "get_auth_service",
        lambda request: FakeAuthService(
            principals_by_session_token={
                "session-101": SimpleNamespace(
                    staff_user_id=101,
                    email="admin@example.com",
                    display_name="Admin User",
                ),
                "session-202": SimpleNamespace(
                    staff_user_id=202,
                    email="staff@example.com",
                    display_name="Staff User",
                ),
            },
        ),
    )
    monkeypatch.setattr(
        admin_auth,
        "get_permission_service",
        lambda request: FakePermissionService({101: {"staff.view"}}),
    )
    monkeypatch.setattr(admin_staff, "get_admin_staff_service", lambda request: staff_service)

    response = await async_client.get(
        "/admin/staff/202",
        cookies={"admin_session": "session-101"},
    )

    assert response.status_code == 200
    assert response.json()["staff_user_id"] == 202
    assert response.json()["requested_by"] == 101
