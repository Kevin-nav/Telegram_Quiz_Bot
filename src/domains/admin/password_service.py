from __future__ import annotations

import base64
import hashlib
import hmac
import secrets


class PasswordService:
    _algorithm = "scrypt"
    _n = 2**14
    _r = 8
    _p = 1
    _dklen = 64
    _salt_bytes = 16

    def hash_password(self, password: str) -> str:
        salt = secrets.token_bytes(self._salt_bytes)
        digest = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=self._n,
            r=self._r,
            p=self._p,
            dklen=self._dklen,
        )
        salt_token = base64.urlsafe_b64encode(salt).decode("ascii")
        digest_token = base64.urlsafe_b64encode(digest).decode("ascii")
        return (
            f"{self._algorithm}${self._n}${self._r}${self._p}"
            f"${salt_token}${digest_token}"
        )

    def verify_password(self, password: str, digest: str | None) -> bool:
        if not digest:
            return False

        algorithm, n, r, p, salt_token, digest_token = digest.split("$", maxsplit=5)
        if algorithm != self._algorithm:
            return False

        salt = base64.urlsafe_b64decode(salt_token.encode("ascii"))
        expected = base64.urlsafe_b64decode(digest_token.encode("ascii"))
        candidate = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=len(expected),
        )
        return hmac.compare_digest(candidate, expected)
