# backend_api/app/core/hashers.py
from __future__ import annotations
import os, base64, hashlib, hmac
from dataclasses import dataclass

try:
    from argon2 import PasswordHasher
    _ARGON2_AVAILABLE = True
except Exception:
    PasswordHasher = None
    _ARGON2_AVAILABLE = False


@dataclass
class Argon2Params:
    time_cost: int = 2
    memory_cost: int = 51200
    parallelism: int = 2
    hash_len: int = 32
    salt_len: int = 16


class Argon2Hasher:
    """Argon2 있으면 Argon2, 없으면 PBKDF2로 폴백."""
    def __init__(self, params: Argon2Params | None = None):
        self.params = params or Argon2Params()
        if _ARGON2_AVAILABLE:
            self._ph = PasswordHasher(
                time_cost=self.params.time_cost,
                memory_cost=self.params.memory_cost,
                parallelism=self.params.parallelism,
                hash_len=self.params.hash_len,
                salt_len=self.params.salt_len,
            )
        else:
            self._ph = None  # PBKDF2 폴백 사용

    def hash(self, plain: str) -> str:
        if _ARGON2_AVAILABLE:
            return self._ph.hash(plain)
        salt = os.urandom(16)
        dk = hashlib.pbkdf2_hmac("sha256", plain.encode(), salt, 200_000, dklen=32)
        return "pbkdf2$" + base64.b64encode(salt + dk).decode()

    def verify(self, hashed: str, plain: str) -> bool:
        if _ARGON2_AVAILABLE and not hashed.startswith("pbkdf2$"):
            try:
                return self._ph.verify(hashed, plain)
            except Exception:
                return False
        if not hashed.startswith("pbkdf2$"):
            return False
        raw = base64.b64decode(hashed.split("$", 1)[1])
        salt, stored = raw[:16], raw[16:]
        dk = hashlib.pbkdf2_hmac("sha256", plain.encode(), salt, 200_000, dklen=32)
        return hmac.compare_digest(stored, dk)

    # (프로젝트 코드와의 호환용 별칭)
    def hash_pin(self, pin: str) -> str:
        return self.hash(pin)

    def verify_pin(self, hashed: str, pin: str) -> bool:
        return self.verify(hashed, pin)


# 필요하면 싱글턴
argon2_hasher = Argon2Hasher()
