"""Conversation logging — writes Q&A pairs to a local SQLite database.

Each successful (or partial) chat completion is appended as one row in the
``conversations`` table.  Errors inside this module are logged and swallowed
so they never interrupt a live SSE stream.

Schema changes are applied via ``backend/migrations`` (see ``db_migrations``).
WAL journal mode is enabled by the migration runner.
"""
from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.prometheus_metrics import inc_sqlite_log_write_failure

logger = logging.getLogger(__name__)

_SQLITE_WRITE_METRIC_CODE = "SQLITE_WRITE_FAILED"


def init_db(db_path: Path) -> None:
    """Apply SQL migrations under ``backend/migrations`` (WAL enabled by runner).

    Raises on migration failure so startup fails loud.
    """
    from backend.services.db_migrations import apply_migrations

    apply_migrations(db_path)
    logger.info("Chat log DB ready: %s", db_path)


def log_conversation(
    *,
    db_path: Path,
    ip: str,
    model: str,
    turn_count: int,
    user_message: str,
    assistant_response: str,
    response_ms: int | None,
    user_name: str = "",
    session_id: str | None = None,
) -> None:
    """Append one conversation record to the SQLite database.

    All errors are caught and logged; this function must never raise so that
    a logging failure cannot break the SSE response stream.
    """
    try:
        created_at = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                """
                INSERT INTO conversations
                    (created_at, ip, model, turn_count, user_message, assistant_response, response_ms, user_name, session_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    created_at,
                    ip,
                    model,
                    turn_count,
                    user_message,
                    assistant_response,
                    response_ms,
                    user_name,
                    session_id,
                ),
            )
    except Exception:
        inc_sqlite_log_write_failure(operation="conversation", code=_SQLITE_WRITE_METRIC_CODE)
        logger.error(
            "Failed to log conversation to SQLite",
            extra={
                "event": "sqlite_log_write_failure",
                "component": "log_service.log_conversation",
                "operation": "conversation",
                "code": _SQLITE_WRITE_METRIC_CODE,
                "db_path": str(db_path),
            },
            exc_info=True,
        )


def upsert_session(
    *,
    db_path: Path,
    session_id: str,
    title: str,
    model: str,
    schema_version: int = 1,
    payload: dict[str, Any],
    created_at: str,
    updated_at: str,
) -> None:
    """Insert or update a persisted chat session with full message history."""
    try:
        encoded_payload = json.dumps(payload, ensure_ascii=False)
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                """
                INSERT INTO sessions (id, title, model, schema_version, created_at, updated_at, messages)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    title=excluded.title,
                    model=excluded.model,
                    schema_version=excluded.schema_version,
                    updated_at=excluded.updated_at,
                    messages=excluded.messages
                """,
                (session_id, title, model, int(schema_version), created_at, updated_at, encoded_payload),
            )
    except Exception:
        inc_sqlite_log_write_failure(operation="session_upsert", code=_SQLITE_WRITE_METRIC_CODE)
        logger.error(
            "Failed to upsert session in SQLite",
            extra={
                "event": "sqlite_log_write_failure",
                "component": "log_service.upsert_session",
                "operation": "session_upsert",
                "code": _SQLITE_WRITE_METRIC_CODE,
                "db_path": str(db_path),
                "session_id": session_id,
            },
            exc_info=True,
        )


def list_sessions(*, db_path: Path) -> list[dict[str, Any]]:
    """Return lightweight session metadata for sidebar listing."""
    try:
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT id, title, model, schema_version, created_at, updated_at
                FROM sessions
                ORDER BY updated_at DESC
                """
            ).fetchall()
        return [dict(r) for r in rows]
    except Exception:
        logger.exception("Failed to list sessions from %s", db_path)
        return []


def get_session(*, db_path: Path, session_id: str) -> dict[str, Any] | None:
    """Return one session including its full messages payload."""
    try:
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                """
                SELECT id, title, model, schema_version, created_at, updated_at, messages
                FROM sessions
                WHERE id = ?
                """,
                (session_id,),
            ).fetchone()
        if row is None:
            return None
        item = dict(row)
        raw_messages = item.get("messages", "[]")
        parsed = json.loads(raw_messages) if isinstance(raw_messages, str) else []
        item["messages"] = parsed if isinstance(parsed, (list, dict)) else []
        return item
    except Exception:
        logger.exception("Failed to fetch session %s from %s", session_id, db_path)
        return None


def delete_session(*, db_path: Path, session_id: str) -> None:
    """Remove one sidebar session row only.

    Rows in ``conversations`` (per-turn audit log) are **not** deleted so operators
    retain Q&A history in SQLite even after a user clears sidebar history.
    """
    try:
        with sqlite3.connect(db_path) as conn:
            conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    except Exception:
        inc_sqlite_log_write_failure(operation="session_delete", code=_SQLITE_WRITE_METRIC_CODE)
        logger.error(
            "Failed to delete session from SQLite",
            extra={
                "event": "sqlite_log_write_failure",
                "component": "log_service.delete_session",
                "operation": "session_delete",
                "code": _SQLITE_WRITE_METRIC_CODE,
                "db_path": str(db_path),
                "session_id": session_id,
            },
            exc_info=True,
        )


def delete_all_sessions(*, db_path: Path) -> None:
    """Remove all rows from ``sessions`` only; ``conversations`` audit rows remain."""
    try:
        with sqlite3.connect(db_path) as conn:
            conn.execute("DELETE FROM sessions")
    except Exception:
        inc_sqlite_log_write_failure(operation="session_delete_all", code=_SQLITE_WRITE_METRIC_CODE)
        logger.error(
            "Failed to delete all sessions from SQLite",
            extra={
                "event": "sqlite_log_write_failure",
                "component": "log_service.delete_all_sessions",
                "operation": "session_delete_all",
                "code": _SQLITE_WRITE_METRIC_CODE,
                "db_path": str(db_path),
            },
            exc_info=True,
        )
