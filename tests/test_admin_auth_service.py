from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from src.domains.admin.auth_service import AuthService
from src.domains.admin.password_service import PasswordService
from src.domains.admin.session_service import SessionService


def test_password_service_verifies_hashed_password():
    service = PasswordService()

    digest = service.hash_password("temp-password")

    assert service.verify_password("temp-password", digest) is True
    assert service.verify_password("wrong-password", digest) is False


def test_session_service_hashes_and_expires_tokens():
    service = SessionService(lifetime=timedelta(hours=2))
    now = datetime(2026, 3, 26, tzinfo=UTC)

    token = service.issue_session_token()
    token_hash = service.hash_session_token(token)

    assert token
    assert token_hash != token
    assert len(token_hash) == 64
    assert service.build_expiry(now=now) == now + timedelta(hours=2)


class FakeStaffUserRepository:
    def __init__(self, users, roles_by_user=None):
        self.users_by_id = {user.id: user for user in users}
        self.users_by_email = {user.email: user for user in users}
        self.roles_by_user = roles_by_user or {}

    async def get_by_id(self, staff_user_id: int):
        return self.users_by_id.get(staff_user_id)

    async def get_by_email(self, email: str):
        return self.users_by_email.get(email)

    async def list_role_codes_for_user(self, staff_user_id: int):
        return list(self.roles_by_user.get(staff_user_id, []))

    async def update_last_login(self, staff_user_id: int, *, last_login_at):
        user = self.users_by_id[staff_user_id]
        user.last_login_at = last_login_at
        return user

    async def set_last_selected_bot(self, staff_user_id: int, *, bot_id: str):
        user = self.users_by_id[staff_user_id]
        user.last_selected_bot_id = bot_id
        return user


class FakePermissionRepository:
    def __init__(self, permissions_by_user=None):
        self.permissions_by_user = permissions_by_user or {}

    async def list_effective_permission_codes_for_user(self, staff_user_id: int):
        return list(self.permissions_by_user.get(staff_user_id, []))


class FakeStaffBotAccessRepository:
    def __init__(self, bot_access_by_user=None):
        self.bot_access_by_user = bot_access_by_user or {}

    async def list_active_bot_ids_for_user(self, staff_user_id: int):
        return list(self.bot_access_by_user.get(staff_user_id, []))


class FakeAdminSessionRepository:
    def __init__(self):
        self.sessions_by_hash = {}
        self.touched_hashes = []
        self.revoked_hashes = []

    async def create_session(self, **payload):
        session = SimpleNamespace(**payload)
        self.sessions_by_hash[payload["session_token_hash"]] = session
        return session

    async def get_active_session_by_token_hash(self, session_token_hash: str, *, now):
        session = self.sessions_by_hash.get(session_token_hash)
        if session is None or session.expires_at <= now:
            return None
        if getattr(session, "revoked_at", None) is not None:
            return None
        return session

    async def touch_session(self, session_token_hash: str, *, last_seen_at):
        self.touched_hashes.append((session_token_hash, last_seen_at))
        return 1

    async def revoke_session(self, session_token_hash: str, *, revoked_at):
        self.revoked_hashes.append((session_token_hash, revoked_at))
        if session_token_hash in self.sessions_by_hash:
            self.sessions_by_hash[session_token_hash].revoked_at = revoked_at
        return 1


@pytest.mark.asyncio
async def test_auth_service_login_and_session_principal_include_bot_scope():
    password_service = PasswordService()
    user = SimpleNamespace(
        id=101,
        email="admin@example.com",
        display_name="Admin User",
        is_active=True,
        password_hash=password_service.hash_password("temp-password"),
        must_change_password=True,
        last_selected_bot_id="tanjah",
        last_login_at=None,
    )
    staff_repo = FakeStaffUserRepository(
        [user],
        roles_by_user={101: ["super_admin"]},
    )
    permission_repo = FakePermissionRepository(
        {101: ["catalog.view", "staff.view"]}
    )
    bot_access_repo = FakeStaffBotAccessRepository(
        {101: ["adarkwa", "tanjah"]}
    )
    session_repo = FakeAdminSessionRepository()
    session_service = SessionService(lifetime=timedelta(hours=1))
    auth_service = AuthService(
        staff_user_repository=staff_repo,
        permission_repository=permission_repo,
        staff_bot_access_repository=bot_access_repo,
        admin_session_repository=session_repo,
        password_service=password_service,
        session_service=session_service,
    )
    now = datetime(2026, 4, 4, 12, 0, tzinfo=UTC)

    login_result = await auth_service.login(
        "admin@example.com",
        "temp-password",
        ip_address="127.0.0.1",
        user_agent="pytest",
        now=now,
    )

    assert login_result is not None
    principal, session_token = login_result
    assert principal.staff_user_id == 101
    assert principal.role_codes == ["super_admin"]
    assert principal.permission_codes == ["catalog.view", "staff.view"]
    assert principal.bot_access == ["adarkwa", "tanjah"]
    assert principal.active_bot_id == "tanjah"
    assert principal.must_change_password is True
    assert user.last_login_at == now

    session_principal = await auth_service.get_principal_for_session_token(
        session_token,
        now=now + timedelta(minutes=5),
    )

    assert session_principal is not None
    assert session_principal.staff_user_id == 101
    assert session_principal.active_bot_id == "tanjah"
    assert len(session_repo.touched_hashes) == 1


@pytest.mark.asyncio
async def test_auth_service_set_active_bot_rejects_unassigned_bot():
    user = SimpleNamespace(
        id=102,
        email="editor@example.com",
        display_name="Editor User",
        is_active=True,
        password_hash=None,
        must_change_password=False,
        last_selected_bot_id=None,
    )
    auth_service = AuthService(
        staff_user_repository=FakeStaffUserRepository(
            [user],
            roles_by_user={102: ["content_editor"]},
        ),
        permission_repository=FakePermissionRepository(
            {102: ["questions.view"]}
        ),
        staff_bot_access_repository=FakeStaffBotAccessRepository(
            {102: ["adarkwa"]}
        ),
        admin_session_repository=FakeAdminSessionRepository(),
    )

    principal = await auth_service.get_principal(102)
    assert principal is not None
    assert principal.active_bot_id == "adarkwa"

    updated = await auth_service.set_active_bot(102, "tanjah")
    assert updated is None
