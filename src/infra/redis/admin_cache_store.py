from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence


class AdminCacheStore:
    def __init__(self, redis_client):
        self.redis_client = redis_client

    async def get_json(
        self,
        namespace: str,
        *,
        bot_id: str | None,
        course_codes: set[str] | None = None,
        extra_parts: Sequence[str | int | None] = (),
    ):
        try:
            version = await self._get_version(namespace, bot_id)
            key = self._payload_key(
                namespace,
                bot_id=bot_id,
                course_codes=course_codes,
                extra_parts=extra_parts,
                version=version,
            )
            payload = await self.redis_client.get(key)
            if not payload:
                return None
            return json.loads(payload)
        except Exception:
            return None

    async def set_json(
        self,
        namespace: str,
        value,
        *,
        bot_id: str | None,
        ttl_seconds: int,
        course_codes: set[str] | None = None,
        extra_parts: Sequence[str | int | None] = (),
    ) -> None:
        try:
            version = await self._get_version(namespace, bot_id)
            key = self._payload_key(
                namespace,
                bot_id=bot_id,
                course_codes=course_codes,
                extra_parts=extra_parts,
                version=version,
            )
            await self.redis_client.set(key, json.dumps(value), ex=ttl_seconds)
        except Exception:
            return

    async def bump_version(self, namespace: str, *, bot_id: str | None) -> None:
        try:
            await self.redis_client.incr(self._version_key(namespace, bot_id))
        except Exception:
            return

    async def _get_version(self, namespace: str, bot_id: str | None) -> int:
        key = self._version_key(namespace, bot_id)
        payload = await self.redis_client.get(key)
        if payload is None:
            await self.redis_client.set(key, "1")
            return 1
        try:
            return max(1, int(payload))
        except (TypeError, ValueError):
            await self.redis_client.set(key, "1")
            return 1

    def _version_key(self, namespace: str, bot_id: str | None) -> str:
        bot_scope = bot_id or "global"
        return f"admin-cache-version:{namespace}:{bot_scope}"

    def _payload_key(
        self,
        namespace: str,
        *,
        bot_id: str | None,
        course_codes: set[str] | None,
        extra_parts: Sequence[str | int | None],
        version: int,
    ) -> str:
        bot_scope = bot_id or "global"
        digest = hashlib.sha256(
            json.dumps(
                {
                    "course_codes": sorted(course_codes or ()),
                    "extra": ["" if value is None else str(value) for value in extra_parts],
                },
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        return f"admin-cache:{namespace}:{bot_scope}:v{version}:{digest}"
