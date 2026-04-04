from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta


class SessionService:
    def __init__(self, *, lifetime: timedelta | None = None):
        self.lifetime = lifetime or timedelta(hours=12)

    def issue_session_token(self) -> str:
        return secrets.token_urlsafe(32)

    def hash_session_token(self, token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def build_expiry(self, *, now: datetime | None = None) -> datetime:
        issued_at = now or datetime.now(UTC)
        return issued_at + self.lifetime
