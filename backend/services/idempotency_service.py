"""SQLite-backed idempotency key service (Phase 13 Wave B)."""

from __future__ import annotations

import hashlib
import logging
import sqlite3
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Protocol

from goat_ai.shared.clocks import Clock, SystemClock
from backend.services.exceptions import PersistenceWriteError
from backend.services.postgres_runtime_support import postgres_connect

logger = logging.getLogger(__name__)

_STATUS_PENDING = "pending"
_STATUS_COMPLETED = "completed"


def build_request_hash(payload: bytes) -> str:
    """Return a stable SHA-256 fingerprint for one request payload."""
    return hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True)
class CompletedResponse:
    status_code: int
    content_type: str
    body: str


@dataclass(frozen=True)
class ClaimResult:
    state: str
    completed: CompletedResponse | None = None


class IdempotencyStore(Protocol):
    """Persistence boundary for idempotent request claim/replay semantics."""

    def claim(
        self,
        *,
        key: str,
        route: str,
        scope: str,
        request_hash: str,
    ) -> ClaimResult: ...

    def store_completed(
        self,
        *,
        key: str,
        route: str,
        scope: str,
        request_hash: str,
        status_code: int,
        content_type: str,
        body: str,
    ) -> None: ...

    def release_pending(
        self,
        *,
        key: str,
        route: str,
        scope: str,
        request_hash: str,
    ) -> None: ...


class SQLiteIdempotencyStore:
    """Persist and replay idempotent responses for selected API boundaries."""

    def __init__(
        self, *, db_path: Path, ttl_sec: int, clock: Clock | None = None
    ) -> None:
        self._db_path = db_path
        self._ttl_sec = max(1, ttl_sec)
        self._clock: Clock = clock if clock is not None else SystemClock()

    def claim(
        self,
        *,
        key: str,
        route: str,
        scope: str,
        request_hash: str,
    ) -> ClaimResult:
        now = self._clock.utc_now()
        now_iso = now.isoformat()
        expires_iso = (now + timedelta(seconds=self._ttl_sec)).isoformat()

        with sqlite3.connect(self._db_path) as conn:
            conn.execute("BEGIN IMMEDIATE;")
            conn.execute(
                "DELETE FROM idempotency_keys WHERE expires_at <= ?",
                (now_iso,),
            )
            row = conn.execute(
                """
                SELECT request_hash, status, response_status, response_content_type, response_body, expires_at
                FROM idempotency_keys
                WHERE key = ? AND route = ? AND scope = ?
                """,
                (key, route, scope),
            ).fetchone()
            if row is None:
                conn.execute(
                    """
                    INSERT INTO idempotency_keys
                        (key, route, scope, request_hash, status, created_at, expires_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        key,
                        route,
                        scope,
                        request_hash,
                        _STATUS_PENDING,
                        now_iso,
                        expires_iso,
                    ),
                )
                conn.commit()
                return ClaimResult(state="claimed")

            stored_hash = str(row[0])
            status = str(row[1])
            response_status = row[2]
            response_content_type = row[3]
            response_body = row[4]
            expires_at = str(row[5])

            if stored_hash != request_hash:
                conn.commit()
                return ClaimResult(state="conflict")

            if expires_at <= now_iso:
                conn.execute(
                    """
                    UPDATE idempotency_keys
                    SET status = ?, response_status = NULL, response_content_type = NULL,
                        response_body = NULL, created_at = ?, expires_at = ?, request_hash = ?
                    WHERE key = ? AND route = ? AND scope = ?
                    """,
                    (
                        _STATUS_PENDING,
                        now_iso,
                        expires_iso,
                        request_hash,
                        key,
                        route,
                        scope,
                    ),
                )
                conn.commit()
                return ClaimResult(state="claimed")

            if (
                status == _STATUS_COMPLETED
                and response_status is not None
                and response_body is not None
            ):
                conn.commit()
                return ClaimResult(
                    state="replay",
                    completed=CompletedResponse(
                        status_code=int(response_status),
                        content_type=str(response_content_type or "application/json"),
                        body=str(response_body),
                    ),
                )

            conn.commit()
            return ClaimResult(state="in_progress")

    def store_completed(
        self,
        *,
        key: str,
        route: str,
        scope: str,
        request_hash: str,
        status_code: int,
        content_type: str,
        body: str,
    ) -> None:
        expires_iso = (
            self._clock.utc_now() + timedelta(seconds=self._ttl_sec)
        ).isoformat()
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """
                UPDATE idempotency_keys
                SET status = ?, response_status = ?, response_content_type = ?,
                    response_body = ?, expires_at = ?
                WHERE key = ? AND route = ? AND scope = ? AND request_hash = ?
                """,
                (
                    _STATUS_COMPLETED,
                    int(status_code),
                    content_type,
                    body,
                    expires_iso,
                    key,
                    route,
                    scope,
                    request_hash,
                ),
            )
            conn.commit()

    def release_pending(
        self,
        *,
        key: str,
        route: str,
        scope: str,
        request_hash: str,
    ) -> None:
        try:
            with sqlite3.connect(self._db_path) as conn:
                conn.execute(
                    """
                    DELETE FROM idempotency_keys
                    WHERE key = ? AND route = ? AND scope = ? AND request_hash = ? AND status = ?
                    """,
                    (key, route, scope, request_hash, _STATUS_PENDING),
                )
                conn.commit()
        except Exception:
            logger.exception(
                "Failed to release pending idempotency key",
                extra={"route": route, "scope": scope},
            )


class PostgresIdempotencyStore:
    """Postgres-backed idempotency store with the same claim/replay semantics."""

    def __init__(self, *, dsn: str, ttl_sec: int, clock: Clock | None = None) -> None:
        self._dsn = dsn
        self._ttl_sec = max(1, ttl_sec)
        self._clock: Clock = clock if clock is not None else SystemClock()

    def claim(
        self,
        *,
        key: str,
        route: str,
        scope: str,
        request_hash: str,
    ) -> ClaimResult:
        now = self._clock.utc_now()
        now_iso = now.isoformat()
        expires_iso = (now + timedelta(seconds=self._ttl_sec)).isoformat()

        with postgres_connect(self._dsn) as conn:
            with conn.transaction():
                conn.execute(
                    "DELETE FROM idempotency_keys WHERE expires_at <= %s",
                    (now_iso,),
                )
                inserted = conn.execute(
                    """
                    INSERT INTO idempotency_keys
                        (key, route, scope, request_hash, status, created_at, expires_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                    RETURNING key
                    """,
                    (
                        key,
                        route,
                        scope,
                        request_hash,
                        _STATUS_PENDING,
                        now_iso,
                        expires_iso,
                    ),
                ).fetchone()
                if inserted is not None:
                    return ClaimResult(state="claimed")

                row = conn.execute(
                    """
                    SELECT request_hash, status, response_status, response_content_type, response_body, expires_at
                    FROM idempotency_keys
                    WHERE key = %s AND route = %s AND scope = %s
                    FOR UPDATE
                    """,
                    (key, route, scope),
                ).fetchone()
                if row is None:
                    inserted_retry = conn.execute(
                        """
                        INSERT INTO idempotency_keys
                            (key, route, scope, request_hash, status, created_at, expires_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT DO NOTHING
                        RETURNING key
                        """,
                        (
                            key,
                            route,
                            scope,
                            request_hash,
                            _STATUS_PENDING,
                            now_iso,
                            expires_iso,
                        ),
                    ).fetchone()
                    if inserted_retry is not None:
                        return ClaimResult(state="claimed")
                    row = conn.execute(
                        """
                        SELECT request_hash, status, response_status, response_content_type, response_body, expires_at
                        FROM idempotency_keys
                        WHERE key = %s AND route = %s AND scope = %s
                        FOR UPDATE
                        """,
                        (key, route, scope),
                    ).fetchone()
                    if row is None:
                        raise PersistenceWriteError(
                            "Failed to claim Postgres idempotency key."
                        )

                stored_hash = str(row["request_hash"])
                status = str(row["status"])
                response_status = row["response_status"]
                response_content_type = row["response_content_type"]
                response_body = row["response_body"]
                expires_at = str(row["expires_at"])

                if stored_hash != request_hash:
                    return ClaimResult(state="conflict")

                if expires_at <= now_iso:
                    conn.execute(
                        """
                        UPDATE idempotency_keys
                        SET status = %s, response_status = NULL, response_content_type = NULL,
                            response_body = NULL, created_at = %s, expires_at = %s, request_hash = %s
                        WHERE key = %s AND route = %s AND scope = %s
                        """,
                        (
                            _STATUS_PENDING,
                            now_iso,
                            expires_iso,
                            request_hash,
                            key,
                            route,
                            scope,
                        ),
                    )
                    return ClaimResult(state="claimed")

                if (
                    status == _STATUS_COMPLETED
                    and response_status is not None
                    and response_body is not None
                ):
                    return ClaimResult(
                        state="replay",
                        completed=CompletedResponse(
                            status_code=int(response_status),
                            content_type=str(
                                response_content_type or "application/json"
                            ),
                            body=str(response_body),
                        ),
                    )

                return ClaimResult(state="in_progress")

    def store_completed(
        self,
        *,
        key: str,
        route: str,
        scope: str,
        request_hash: str,
        status_code: int,
        content_type: str,
        body: str,
    ) -> None:
        expires_iso = (
            self._clock.utc_now() + timedelta(seconds=self._ttl_sec)
        ).isoformat()
        try:
            with postgres_connect(self._dsn) as conn:
                conn.execute(
                    """
                    UPDATE idempotency_keys
                    SET status = %s, response_status = %s, response_content_type = %s,
                        response_body = %s, expires_at = %s
                    WHERE key = %s AND route = %s AND scope = %s AND request_hash = %s
                    """,
                    (
                        _STATUS_COMPLETED,
                        int(status_code),
                        content_type,
                        body,
                        expires_iso,
                        key,
                        route,
                        scope,
                        request_hash,
                    ),
                )
        except Exception as exc:
            raise PersistenceWriteError(
                "Failed to idempotency store completed."
            ) from exc

    def release_pending(
        self,
        *,
        key: str,
        route: str,
        scope: str,
        request_hash: str,
    ) -> None:
        try:
            with postgres_connect(self._dsn) as conn:
                conn.execute(
                    """
                    DELETE FROM idempotency_keys
                    WHERE key = %s AND route = %s AND scope = %s AND request_hash = %s AND status = %s
                    """,
                    (key, route, scope, request_hash, _STATUS_PENDING),
                )
        except Exception:
            logger.exception(
                "Failed to release pending Postgres idempotency key",
                extra={"route": route, "scope": scope},
            )
