from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol

from backend.services.postgres_runtime_support import postgres_connect

AccountProvider = Literal["local", "google"]


@dataclass(frozen=True)
class AccountUser:
    id: str
    email: str
    password_hash: str
    display_name: str
    primary_provider: AccountProvider
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class AccountUserIdentity:
    id: str
    user_id: str
    provider: AccountProvider
    provider_subject: str
    email: str
    created_at: str
    updated_at: str


class AccountRepository(Protocol):
    def get_user_by_email(self, email: str) -> AccountUser | None: ...

    def get_user_by_id(self, user_id: str) -> AccountUser | None: ...

    def get_user_by_identity(
        self, *, provider: AccountProvider, provider_subject: str
    ) -> AccountUser | None: ...

    def get_identity(
        self, *, provider: AccountProvider, provider_subject: str
    ) -> AccountUserIdentity | None: ...

    def create_user(self, user: AccountUser) -> None: ...

    def update_user(
        self,
        *,
        user_id: str,
        display_name: str,
        primary_provider: AccountProvider,
        password_hash: str,
        updated_at: str,
    ) -> None: ...

    def create_identity(self, identity: AccountUserIdentity) -> None: ...


def normalize_account_email(email: str) -> str:
    return email.strip().lower()


class SQLiteAccountRepository:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path

    def get_user_by_email(self, email: str) -> AccountUser | None:
        with sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                """
                SELECT id, email, password_hash, display_name, primary_provider, created_at, updated_at
                FROM auth_users
                WHERE email = ?
                """,
                (normalize_account_email(email),),
            ).fetchone()
        return AccountUser(**dict(row)) if row is not None else None

    def get_user_by_id(self, user_id: str) -> AccountUser | None:
        with sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                """
                SELECT id, email, password_hash, display_name, primary_provider, created_at, updated_at
                FROM auth_users
                WHERE id = ?
                """,
                (user_id,),
            ).fetchone()
        return AccountUser(**dict(row)) if row is not None else None

    def get_user_by_identity(
        self, *, provider: AccountProvider, provider_subject: str
    ) -> AccountUser | None:
        with sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                """
                SELECT u.id, u.email, u.password_hash, u.display_name, u.primary_provider, u.created_at, u.updated_at
                FROM auth_users AS u
                JOIN auth_user_identities AS i
                  ON i.user_id = u.id
                WHERE i.provider = ? AND i.provider_subject = ?
                """,
                (provider, provider_subject),
            ).fetchone()
        return AccountUser(**dict(row)) if row is not None else None

    def get_identity(
        self, *, provider: AccountProvider, provider_subject: str
    ) -> AccountUserIdentity | None:
        with sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                """
                SELECT id, user_id, provider, provider_subject, email, created_at, updated_at
                FROM auth_user_identities
                WHERE provider = ? AND provider_subject = ?
                """,
                (provider, provider_subject),
            ).fetchone()
        return AccountUserIdentity(**dict(row)) if row is not None else None

    def create_user(self, user: AccountUser) -> None:
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """
                INSERT INTO auth_users
                    (id, email, password_hash, display_name, primary_provider, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user.id,
                    normalize_account_email(user.email),
                    user.password_hash,
                    user.display_name,
                    user.primary_provider,
                    user.created_at,
                    user.updated_at,
                ),
            )

    def update_user(
        self,
        *,
        user_id: str,
        display_name: str,
        primary_provider: AccountProvider,
        password_hash: str,
        updated_at: str,
    ) -> None:
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """
                UPDATE auth_users
                SET display_name = ?, primary_provider = ?, password_hash = ?, updated_at = ?
                WHERE id = ?
                """,
                (display_name, primary_provider, password_hash, updated_at, user_id),
            )

    def create_identity(self, identity: AccountUserIdentity) -> None:
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """
                INSERT INTO auth_user_identities
                    (id, user_id, provider, provider_subject, email, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    identity.id,
                    identity.user_id,
                    identity.provider,
                    identity.provider_subject,
                    normalize_account_email(identity.email),
                    identity.created_at,
                    identity.updated_at,
                ),
            )


class PostgresAccountRepository:
    def __init__(self, dsn: str) -> None:
        self._dsn = dsn

    def get_user_by_email(self, email: str) -> AccountUser | None:
        with postgres_connect(self._dsn) as conn:
            row = conn.execute(
                """
                SELECT id, email, password_hash, display_name, primary_provider, created_at, updated_at
                FROM auth_users
                WHERE email = %s
                """,
                (normalize_account_email(email),),
            ).fetchone()
        return AccountUser(**dict(row)) if row is not None else None

    def get_user_by_id(self, user_id: str) -> AccountUser | None:
        with postgres_connect(self._dsn) as conn:
            row = conn.execute(
                """
                SELECT id, email, password_hash, display_name, primary_provider, created_at, updated_at
                FROM auth_users
                WHERE id = %s
                """,
                (user_id,),
            ).fetchone()
        return AccountUser(**dict(row)) if row is not None else None

    def get_user_by_identity(
        self, *, provider: AccountProvider, provider_subject: str
    ) -> AccountUser | None:
        with postgres_connect(self._dsn) as conn:
            row = conn.execute(
                """
                SELECT u.id, u.email, u.password_hash, u.display_name, u.primary_provider, u.created_at, u.updated_at
                FROM auth_users AS u
                JOIN auth_user_identities AS i
                  ON i.user_id = u.id
                WHERE i.provider = %s AND i.provider_subject = %s
                """,
                (provider, provider_subject),
            ).fetchone()
        return AccountUser(**dict(row)) if row is not None else None

    def get_identity(
        self, *, provider: AccountProvider, provider_subject: str
    ) -> AccountUserIdentity | None:
        with postgres_connect(self._dsn) as conn:
            row = conn.execute(
                """
                SELECT id, user_id, provider, provider_subject, email, created_at, updated_at
                FROM auth_user_identities
                WHERE provider = %s AND provider_subject = %s
                """,
                (provider, provider_subject),
            ).fetchone()
        return AccountUserIdentity(**dict(row)) if row is not None else None

    def create_user(self, user: AccountUser) -> None:
        with postgres_connect(self._dsn) as conn:
            with conn.transaction():
                conn.execute(
                    """
                    INSERT INTO auth_users
                        (id, email, password_hash, display_name, primary_provider, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        user.id,
                        normalize_account_email(user.email),
                        user.password_hash,
                        user.display_name,
                        user.primary_provider,
                        user.created_at,
                        user.updated_at,
                    ),
                )

    def update_user(
        self,
        *,
        user_id: str,
        display_name: str,
        primary_provider: AccountProvider,
        password_hash: str,
        updated_at: str,
    ) -> None:
        with postgres_connect(self._dsn) as conn:
            with conn.transaction():
                conn.execute(
                    """
                    UPDATE auth_users
                    SET display_name = %s, primary_provider = %s, password_hash = %s, updated_at = %s
                    WHERE id = %s
                    """,
                    (
                        display_name,
                        primary_provider,
                        password_hash,
                        updated_at,
                        user_id,
                    ),
                )

    def create_identity(self, identity: AccountUserIdentity) -> None:
        with postgres_connect(self._dsn) as conn:
            with conn.transaction():
                conn.execute(
                    """
                    INSERT INTO auth_user_identities
                        (id, user_id, provider, provider_subject, email, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        identity.id,
                        identity.user_id,
                        identity.provider,
                        identity.provider_subject,
                        normalize_account_email(identity.email),
                        identity.created_at,
                        identity.updated_at,
                    ),
                )
