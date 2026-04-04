from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from src.bot.runtime_config import ADARKWA_BOT_ID
from src.domains.admin.password_service import PasswordService
from src.domains.admin.session_service import SessionService
from src.infra.db.models.staff_user import StaffUser
from src.infra.db.repositories.admin_session_repository import AdminSessionRepository
from src.infra.db.repositories.permission_repository import PermissionRepository
from src.infra.db.repositories.staff_bot_access_repository import (
    StaffBotAccessRepository,
)
from src.infra.db.repositories.staff_user_repository import StaffUserRepository


@dataclass(slots=True)
class AdminPrincipal:
    staff_user_id: int
    email: str
    display_name: str | None = None
    role_codes: list[str] | None = None
    permission_codes: list[str] | None = None
    bot_access: list[str] | None = None
    active_bot_id: str | None = None
    must_change_password: bool = False


class AuthService:
    def __init__(
        self,
        staff_user_repository: StaffUserRepository | None = None,
        permission_repository: PermissionRepository | None = None,
        staff_bot_access_repository: StaffBotAccessRepository | None = None,
        admin_session_repository: AdminSessionRepository | None = None,
        password_service: PasswordService | None = None,
        session_service: SessionService | None = None,
    ):
        self.staff_user_repository = staff_user_repository or StaffUserRepository()
        self.permission_repository = permission_repository or PermissionRepository()
        self.staff_bot_access_repository = (
            staff_bot_access_repository or StaffBotAccessRepository()
        )
        self.admin_session_repository = (
            admin_session_repository or AdminSessionRepository()
        )
        self.password_service = password_service or PasswordService()
        self.session_service = session_service or SessionService()

    async def get_staff_user(self, staff_user_id: int) -> StaffUser | None:
        return await self.staff_user_repository.get_by_id(staff_user_id)

    async def get_principal(self, staff_user_id: int) -> AdminPrincipal | None:
        staff_user = await self.get_staff_user(staff_user_id)
        if staff_user is None or not staff_user.is_active:
            return None

        role_codes = await self.staff_user_repository.list_role_codes_for_user(
            staff_user.id
        )
        permission_codes = (
            await self.permission_repository.list_effective_permission_codes_for_user(
                staff_user.id
            )
        )
        bot_access = (
            await self.staff_bot_access_repository.list_active_bot_ids_for_user(
                staff_user.id
            )
        )

        return AdminPrincipal(
            staff_user_id=staff_user.id,
            email=staff_user.email,
            display_name=staff_user.display_name,
            role_codes=role_codes,
            permission_codes=permission_codes,
            bot_access=bot_access,
            active_bot_id=self._resolve_active_bot_id(
                bot_access,
                staff_user.last_selected_bot_id,
            ),
            must_change_password=bool(
                getattr(staff_user, "must_change_password", False)
            ),
        )

    async def login(
        self,
        email: str,
        password: str,
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
        now: datetime | None = None,
    ) -> tuple[AdminPrincipal, str] | None:
        issued_at = now or datetime.now(UTC)
        staff_user = await self.staff_user_repository.get_by_email(email.strip())
        if staff_user is None or not staff_user.is_active:
            return None
        if not self.password_service.verify_password(
            password,
            getattr(staff_user, "password_hash", None),
        ):
            return None

        principal = await self.get_principal(staff_user.id)
        if principal is None:
            return None

        session_token = self.session_service.issue_session_token()
        await self.admin_session_repository.create_session(
            staff_user_id=staff_user.id,
            session_token_hash=self.session_service.hash_session_token(session_token),
            expires_at=self.session_service.build_expiry(now=issued_at),
            ip_address=ip_address,
            user_agent=user_agent,
        )
        await self.staff_user_repository.update_last_login(
            staff_user.id,
            last_login_at=issued_at,
        )
        return principal, session_token

    async def get_principal_for_session_token(
        self,
        session_token: str,
        *,
        now: datetime | None = None,
    ) -> AdminPrincipal | None:
        checked_at = now or datetime.now(UTC)
        session_token_hash = self.session_service.hash_session_token(session_token)
        admin_session = (
            await self.admin_session_repository.get_active_session_by_token_hash(
                session_token_hash,
                now=checked_at,
            )
        )
        if admin_session is None:
            return None

        await self.admin_session_repository.touch_session(
            session_token_hash,
            last_seen_at=checked_at,
        )
        return await self.get_principal(admin_session.staff_user_id)

    async def logout(self, session_token: str, *, now: datetime | None = None) -> None:
        revoked_at = now or datetime.now(UTC)
        await self.admin_session_repository.revoke_session(
            self.session_service.hash_session_token(session_token),
            revoked_at=revoked_at,
        )

    async def set_password(
        self,
        staff_user_id: int,
        *,
        current_password: str,
        new_password: str,
        now: datetime | None = None,
    ) -> AdminPrincipal | None:
        staff_user = await self.get_staff_user(staff_user_id)
        if staff_user is None or not staff_user.is_active:
            return None
        if not self.password_service.verify_password(
            current_password,
            getattr(staff_user, "password_hash", None),
        ):
            return None

        await self.staff_user_repository.update_password(
            staff_user_id,
            password_hash=self.password_service.hash_password(new_password),
            must_change_password=False,
            password_updated_at=now or datetime.now(UTC),
        )
        return await self.get_principal(staff_user_id)

    async def set_active_bot(self, staff_user_id: int, bot_id: str) -> AdminPrincipal | None:
        principal = await self.get_principal(staff_user_id)
        if principal is None or bot_id not in (principal.bot_access or []):
            return None
        await self.staff_user_repository.set_last_selected_bot(
            staff_user_id,
            bot_id=bot_id,
        )
        return await self.get_principal(staff_user_id)

    def _resolve_active_bot_id(
        self,
        bot_access: list[str],
        last_selected_bot_id: str | None,
    ) -> str | None:
        if not bot_access:
            return None
        if len(bot_access) == 1:
            return bot_access[0]
        if last_selected_bot_id in bot_access:
            return last_selected_bot_id
        if ADARKWA_BOT_ID in bot_access:
            return ADARKWA_BOT_ID
        return bot_access[0]
