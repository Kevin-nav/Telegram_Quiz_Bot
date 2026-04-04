from __future__ import annotations

from datetime import datetime

from sqlalchemy import select, update

from src.infra.db.models.admin_session import AdminSession
from src.infra.db.session import AsyncSessionLocal


class AdminSessionRepository:
    def __init__(self, session_factory=AsyncSessionLocal):
        self.session_factory = session_factory

    async def create_session(
        self,
        *,
        staff_user_id: int,
        session_token_hash: str,
        expires_at: datetime,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AdminSession:
        async with self.session_factory() as session:
            admin_session = AdminSession(
                staff_user_id=staff_user_id,
                session_token_hash=session_token_hash,
                expires_at=expires_at,
                ip_address=ip_address,
                user_agent=user_agent,
                last_seen_at=None,
                revoked_at=None,
            )
            session.add(admin_session)
            await session.commit()
            await session.refresh(admin_session)
            return admin_session

    async def get_active_session_by_token_hash(
        self,
        session_token_hash: str,
        *,
        now: datetime,
    ) -> AdminSession | None:
        async with self.session_factory() as session:
            result = await session.execute(
                select(AdminSession).where(
                    AdminSession.session_token_hash == session_token_hash,
                    AdminSession.revoked_at.is_(None),
                    AdminSession.expires_at > now,
                )
            )
            return result.scalar_one_or_none()

    async def revoke_session(
        self,
        session_token_hash: str,
        *,
        revoked_at: datetime,
    ) -> int:
        async with self.session_factory() as session:
            result = await session.execute(
                update(AdminSession)
                .where(
                    AdminSession.session_token_hash == session_token_hash,
                    AdminSession.revoked_at.is_(None),
                )
                .values(revoked_at=revoked_at)
            )
            await session.commit()
            return int(result.rowcount or 0)

    async def revoke_sessions_for_user(
        self,
        staff_user_id: int,
        *,
        revoked_at: datetime,
    ) -> int:
        async with self.session_factory() as session:
            result = await session.execute(
                update(AdminSession)
                .where(
                    AdminSession.staff_user_id == staff_user_id,
                    AdminSession.revoked_at.is_(None),
                )
                .values(revoked_at=revoked_at)
            )
            await session.commit()
            return int(result.rowcount or 0)

    async def touch_session(
        self,
        session_token_hash: str,
        *,
        last_seen_at: datetime,
    ) -> int:
        async with self.session_factory() as session:
            result = await session.execute(
                update(AdminSession)
                .where(
                    AdminSession.session_token_hash == session_token_hash,
                    AdminSession.revoked_at.is_(None),
                )
                .values(last_seen_at=last_seen_at)
            )
            await session.commit()
            return int(result.rowcount or 0)

    async def get_session_by_token_hash(
        self,
        session_token_hash: str,
    ) -> AdminSession | None:
        async with self.session_factory() as session:
            result = await session.execute(
                select(AdminSession).where(
                    AdminSession.session_token_hash == session_token_hash
                )
            )
            return result.scalar_one_or_none()
