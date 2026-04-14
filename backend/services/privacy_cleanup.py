"""Governed cleanup helpers for privacy-sensitive runtime state."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from backend.services.postgres_runtime_support import postgres_connect
from goat_ai.config.settings import Settings


@dataclass(frozen=True)
class OwnerlessHistoryPurgeSummary:
    dry_run: bool
    backend: str
    matched_session_ids: list[str]
    sessions_deleted: int
    session_messages_deleted: int
    chat_artifacts_deleted: int
    conversations_deleted: int


def purge_ownerless_history(
    *,
    settings: Settings,
    dry_run: bool = False,
) -> OwnerlessHistoryPurgeSummary:
    if settings.runtime_metadata_backend == "postgres":
        return _purge_ownerless_history_postgres(
            dsn=settings.runtime_postgres_dsn,
            dry_run=dry_run,
        )
    return _purge_ownerless_history_sqlite(
        db_path=settings.log_db_path,
        dry_run=dry_run,
    )


def _purge_ownerless_history_sqlite(
    *, db_path: Path, dry_run: bool
) -> OwnerlessHistoryPurgeSummary:
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        session_ids = _select_ownerless_session_ids(
            conn.execute("SELECT id FROM sessions WHERE owner_id = ''").fetchall()
        )
        if dry_run or not session_ids:
            return OwnerlessHistoryPurgeSummary(
                dry_run=dry_run,
                backend="sqlite",
                matched_session_ids=session_ids,
                sessions_deleted=0 if dry_run else len(session_ids),
                session_messages_deleted=0,
                chat_artifacts_deleted=0,
                conversations_deleted=0,
            )
        conn.execute("BEGIN IMMEDIATE")
        session_messages_deleted = _sqlite_delete_by_session_ids(
            conn,
            table_name="session_messages",
            session_ids=session_ids,
        )
        chat_artifacts_deleted = _sqlite_delete_by_session_ids(
            conn,
            table_name="chat_artifacts",
            session_ids=session_ids,
        )
        conversations_deleted = _sqlite_delete_by_session_ids(
            conn,
            table_name="conversations",
            session_ids=session_ids,
        )
        placeholders = ", ".join("?" for _ in session_ids)
        cursor = conn.execute(
            f"DELETE FROM sessions WHERE id IN ({placeholders})",
            tuple(session_ids),
        )
        conn.commit()
    return OwnerlessHistoryPurgeSummary(
        dry_run=False,
        backend="sqlite",
        matched_session_ids=session_ids,
        sessions_deleted=cursor.rowcount or 0,
        session_messages_deleted=session_messages_deleted,
        chat_artifacts_deleted=chat_artifacts_deleted,
        conversations_deleted=conversations_deleted,
    )


def _sqlite_delete_by_session_ids(
    conn: sqlite3.Connection,
    *,
    table_name: str,
    session_ids: list[str],
) -> int:
    if not session_ids:
        return 0
    placeholders = ", ".join("?" for _ in session_ids)
    cursor = conn.execute(
        f"DELETE FROM {table_name} WHERE session_id IN ({placeholders})",
        tuple(session_ids),
    )
    return cursor.rowcount or 0


def _purge_ownerless_history_postgres(
    *, dsn: str, dry_run: bool
) -> OwnerlessHistoryPurgeSummary:
    with postgres_connect(dsn) as conn:
        session_ids = _select_ownerless_session_ids(
            conn.execute(
                "SELECT id FROM sessions WHERE owner_id = %s", ("",)
            ).fetchall()
        )
        if dry_run or not session_ids:
            return OwnerlessHistoryPurgeSummary(
                dry_run=dry_run,
                backend="postgres",
                matched_session_ids=session_ids,
                sessions_deleted=0 if dry_run else len(session_ids),
                session_messages_deleted=0,
                chat_artifacts_deleted=0,
                conversations_deleted=0,
            )
        with conn.transaction():
            session_messages_deleted = _postgres_delete_by_session_ids(
                conn,
                table_name="session_messages",
                session_ids=session_ids,
            )
            chat_artifacts_deleted = _postgres_delete_by_session_ids(
                conn,
                table_name="chat_artifacts",
                session_ids=session_ids,
            )
            conversations_deleted = _postgres_delete_by_session_ids(
                conn,
                table_name="conversations",
                session_ids=session_ids,
            )
            placeholders = ", ".join(["%s"] * len(session_ids))
            cursor = conn.execute(
                f"DELETE FROM sessions WHERE id IN ({placeholders})",
                tuple(session_ids),
            )
    return OwnerlessHistoryPurgeSummary(
        dry_run=False,
        backend="postgres",
        matched_session_ids=session_ids,
        sessions_deleted=cursor.rowcount or 0,
        session_messages_deleted=session_messages_deleted,
        chat_artifacts_deleted=chat_artifacts_deleted,
        conversations_deleted=conversations_deleted,
    )


def _postgres_delete_by_session_ids(
    conn,
    *,
    table_name: str,
    session_ids: list[str],
) -> int:
    if not session_ids:
        return 0
    placeholders = ", ".join(["%s"] * len(session_ids))
    cursor = conn.execute(
        f"DELETE FROM {table_name} WHERE session_id IN ({placeholders})",
        tuple(session_ids),
    )
    return cursor.rowcount or 0


def _select_ownerless_session_ids(rows: list[object]) -> list[str]:
    ids: list[str] = []
    for row in rows:
        if isinstance(row, sqlite3.Row):
            value = row["id"]
        else:
            value = row["id"]  # type: ignore[index]
        session_id = str(value or "").strip()
        if session_id:
            ids.append(session_id)
    return ids
