from __future__ import annotations

from pwdlib import PasswordHash

_PASSWORD_HASHER = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return _PASSWORD_HASHER.hash(password.strip())


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _PASSWORD_HASHER.verify(password.strip(), password_hash.strip())
    except Exception:
        return False
