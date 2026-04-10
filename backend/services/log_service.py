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
from backend.services.exceptions import (
    PersistenceReadError,
    PersistenceWriteError,
    SessionNotFoundError,
)

logger = logging.getLogger(__name__)

_SQLITE_WRITE_METRIC_CODE = "SQLITE_WRITE_FAILED"


def _raise_persistence_read_error(
    *,
    operation: str,
    db_path: Path,
    exc: Exception,
    resource_id: str | None = None,
) -> None:
    logger.exception(
        "Failed to %s in SQLite",
        operation.replace("_", " "),
        extra={
            "event": "sqlite_read_failure",
            "component": f"log_service.{operation}",
            "operation": operation,
            "db_path": str(db_path),
            "resource_id": resource_id or "",
        },
    )
    raise PersistenceReadError(f"Failed to {operation.replace('_', ' ')}.") from exc


def _raise_persistence_write_error(
    *,
    operation: str,
    db_path: Path,
    exc: Exception,
    session_id: str | None = None,
    artifact_id: str | None = None,
) -> None:
    inc_sqlite_log_write_failure(
        operation=operation, code=_SQLITE_WRITE_METRIC_CODE
    )
    logger.error(
        "Failed to %s in SQLite",
        operation.replace("_", " "),
        extra={
            "event": "sqlite_log_write_failure",
            "component": f"log_service.{operation}",
            "operation": operation,
            "code": _SQLITE_WRITE_METRIC_CODE,
            "db_path": str(db_path),
            "session_id": session_id or "",
            "artifact_id": artifact_id or "",
        },
        exc_info=True,
    )
    raise PersistenceWriteError(
        f"Failed to {operation.replace('_', ' ')}."
    ) from exc


def _payload_visible_messages(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract chat message dicts from a versioned session payload for ``session_messages`` rows."""
    raw = payload.get("messages", [])
    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        content = item.get("content")
        if role not in {"user", "assistant", "system"} or not isinstance(content, str):
            continue
        row: dict[str, Any] = {"role": str(role), "content": content}
        raw_ids = item.get("image_attachment_ids")
        if isinstance(raw_ids, list) and raw_ids:
            ids: list[str] = []
            for x in raw_ids:
                if isinstance(x, str) and x.strip():
                    ids.append(x.strip())
            if ids:
                row["image_attachment_ids"] = ids
        raw_artifacts = item.get("artifacts")
        if isinstance(raw_artifacts, list) and raw_artifacts:
            row["artifacts"] = raw_artifacts
        out.append(row)
    return out


def _session_messages_table_exists(conn: sqlite3.Connection) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='session_messages'",
    ).fetchone()
    return row is not None


def _sessions_has_owner_id_column(conn: sqlite3.Connection) -> bool:
    cols = [r[1] for r in conn.execute("PRAGMA table_info(sessions)").fetchall()]
    return "owner_id" in cols


def _sessions_has_tenant_columns(conn: sqlite3.Connection) -> bool:
    cols = [r[1] for r in conn.execute("PRAGMA table_info(sessions)").fetchall()]
    return "tenant_id" in cols and "principal_id" in cols


def _chat_artifacts_has_tenant_columns(conn: sqlite3.Connection) -> bool:
    cols = [r[1] for r in conn.execute("PRAGMA table_info(chat_artifacts)").fetchall()]
    return "tenant_id" in cols and "principal_id" in cols


def _replace_session_messages(
    conn: sqlite3.Connection,
    *,
    session_id: str,
    payload: dict[str, Any],
) -> None:
    """Sync ``session_messages`` to match the current snapshot payload (delete + insert)."""
    if not _session_messages_table_exists(conn):
        return
    conn.execute("DELETE FROM session_messages WHERE session_id = ?", (session_id,))
    now = datetime.now(timezone.utc).isoformat()
    for seq, msg in enumerate(_payload_visible_messages(payload)):
        ids_json = (
            json.dumps(msg["image_attachment_ids"], ensure_ascii=False)
            if msg.get("image_attachment_ids")
            else None
        )
        artifacts_json = (
            json.dumps(msg["artifacts"], ensure_ascii=False)
            if msg.get("artifacts")
            else None
        )
        conn.execute(
            """
            INSERT INTO session_messages (session_id, seq, role, content, image_attachment_ids, artifacts_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                seq,
                msg["role"],
                msg["content"],
                ids_json,
                artifacts_json,
                now,
            ),
        )


def _fetch_session_messages_list(
    conn: sqlite3.Connection, session_id: str
) -> list[dict[str, Any]] | None:
    """Return ordered message dicts from ``session_messages``, or ``None`` if no rows."""
    if not _session_messages_table_exists(conn):
        return None
    rows = conn.execute(
        """
        SELECT role, content, image_attachment_ids, artifacts_json
        FROM session_messages
        WHERE session_id = ?
        ORDER BY seq ASC
        """,
        (session_id,),
    ).fetchall()
    if not rows:
        return None
    out: list[dict[str, Any]] = []
    for role, content, ids_raw, artifacts_raw in rows:
        item: dict[str, Any] = {"role": str(role), "content": str(content)}
        if isinstance(ids_raw, str) and ids_raw.strip():
            try:
                parsed = json.loads(ids_raw)
            except json.JSONDecodeError:
                parsed = None
            if isinstance(parsed, list) and parsed:
                item["image_attachment_ids"] = parsed
        if isinstance(artifacts_raw, str) and artifacts_raw.strip():
            try:
                parsed_artifacts = json.loads(artifacts_raw)
            except json.JSONDecodeError:
                parsed_artifacts = None
            if isinstance(parsed_artifacts, list) and parsed_artifacts:
                item["artifacts"] = parsed_artifacts
        out.append(item)
    return out


def _chat_artifacts_table_exists(conn: sqlite3.Connection) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='chat_artifacts'",
    ).fetchone()
    return row is not None


def _merge_session_messages_into_item(
    *,
    messages_value: list[dict[str, Any]] | dict[str, Any] | Any,
    normalized: list[dict[str, Any]],
) -> list[dict[str, Any]] | dict[str, Any]:
    """Prefer normalized rows for the visible message list; keep dict envelope fields when present."""
    if isinstance(messages_value, dict):
        merged = dict(messages_value)
        merged["messages"] = normalized
        return merged
    return normalized


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
        inc_sqlite_log_write_failure(
            operation="conversation", code=_SQLITE_WRITE_METRIC_CODE
        )
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
    owner_id: str = "",
    tenant_id: str = "tenant:default",
    principal_id: str = "",
) -> None:
    """Insert or update a persisted chat session with full message history."""
    try:
        encoded_payload = json.dumps(payload, ensure_ascii=False)
        with sqlite3.connect(db_path) as conn:
            try:
                conn.execute("BEGIN IMMEDIATE")
                if _sessions_has_owner_id_column(conn):
                    if _sessions_has_tenant_columns(conn):
                        conn.execute(
                            """
                            INSERT INTO sessions (id, title, model, schema_version, created_at, updated_at, messages, owner_id, tenant_id, principal_id)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ON CONFLICT(id) DO UPDATE SET
                                title=excluded.title,
                                model=excluded.model,
                                schema_version=excluded.schema_version,
                                updated_at=excluded.updated_at,
                                messages=excluded.messages,
                                owner_id=excluded.owner_id,
                                tenant_id=excluded.tenant_id,
                                principal_id=excluded.principal_id
                            """,
                            (
                                session_id,
                                title,
                                model,
                                int(schema_version),
                                created_at,
                                updated_at,
                                encoded_payload,
                                owner_id,
                                tenant_id,
                                principal_id,
                            ),
                        )
                    else:
                        conn.execute(
                            """
                            INSERT INTO sessions (id, title, model, schema_version, created_at, updated_at, messages, owner_id)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            ON CONFLICT(id) DO UPDATE SET
                                title=excluded.title,
                                model=excluded.model,
                                schema_version=excluded.schema_version,
                                updated_at=excluded.updated_at,
                                messages=excluded.messages,
                                owner_id=excluded.owner_id
                            """,
                            (
                                session_id,
                                title,
                                model,
                                int(schema_version),
                                created_at,
                                updated_at,
                                encoded_payload,
                                owner_id,
                            ),
                        )
                else:
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
                        (
                            session_id,
                            title,
                            model,
                            int(schema_version),
                            created_at,
                            updated_at,
                            encoded_payload,
                        ),
                    )
                _replace_session_messages(conn, session_id=session_id, payload=payload)
                conn.commit()
            except Exception:
                conn.rollback()
                raise
    except Exception as exc:
        _raise_persistence_write_error(
            operation="session_upsert",
            db_path=db_path,
            exc=exc,
            session_id=session_id,
        )


def rename_session_title(*, db_path: Path, session_id: str, title: str) -> None:
    """Rename one persisted chat session without touching its message payload."""
    try:
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(db_path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            cursor = conn.execute(
                """
                UPDATE sessions
                SET title = ?, updated_at = ?
                WHERE id = ?
                """,
                (title, now, session_id),
            )
            if cursor.rowcount == 0:
                conn.rollback()
                raise SessionNotFoundError("Session not found")
            conn.commit()
    except SessionNotFoundError:
        raise
    except Exception as exc:
        _raise_persistence_write_error(
            operation="session_rename",
            db_path=db_path,
            exc=exc,
            session_id=session_id,
        )


def list_sessions(
    *,
    db_path: Path,
    owner_filter: str | None = None,
    tenant_filter: str | None = None,
) -> list[dict[str, Any]]:
    """Return lightweight session metadata for sidebar listing."""
    try:
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            sel = (
                "id, title, model, schema_version, created_at, updated_at, owner_id, tenant_id, principal_id"
                if _sessions_has_tenant_columns(conn)
                else (
                    "id, title, model, schema_version, created_at, updated_at, owner_id"
                    if _sessions_has_owner_id_column(conn)
                    else "id, title, model, schema_version, created_at, updated_at"
                )
            )
            clauses: list[str] = []
            params: list[str] = []
            if owner_filter is not None and _sessions_has_owner_id_column(conn):
                clauses.append("owner_id = ?")
                params.append(owner_filter)
            if tenant_filter is not None and _sessions_has_tenant_columns(conn):
                clauses.append("tenant_id = ?")
                params.append(tenant_filter)
            where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
            rows = conn.execute(
                f"""
                SELECT {sel}
                FROM sessions
                {where_sql}
                ORDER BY updated_at DESC
                """,
                tuple(params),
            ).fetchall()
        return [dict(r) for r in rows]
    except Exception as exc:
        _raise_persistence_read_error(
            operation="session_list",
            db_path=db_path,
            exc=exc,
        )


def get_session(*, db_path: Path, session_id: str) -> dict[str, Any] | None:
    """Return one session including its full messages payload."""
    try:
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            sel_msg = (
                "id, title, model, schema_version, created_at, updated_at, messages, owner_id, tenant_id, principal_id"
                if _sessions_has_tenant_columns(conn)
                else (
                    "id, title, model, schema_version, created_at, updated_at, messages, owner_id"
                    if _sessions_has_owner_id_column(conn)
                    else "id, title, model, schema_version, created_at, updated_at, messages"
                )
            )
            row = conn.execute(
                f"""
                SELECT {sel_msg}
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
            normalized = _fetch_session_messages_list(conn, session_id)
        if normalized is not None:
            item["messages"] = _merge_session_messages_into_item(
                messages_value=item["messages"],
                normalized=normalized,
            )
        return item
    except Exception as exc:
        _raise_persistence_read_error(
            operation="session_get",
            db_path=db_path,
            exc=exc,
            resource_id=session_id,
        )


def delete_session(*, db_path: Path, session_id: str) -> None:
    """Remove one sidebar session row only.

    Rows in ``conversations`` (per-turn audit log) are **not** deleted so operators
    retain Q&A history in SQLite even after a user clears sidebar history.
    """
    try:
        with sqlite3.connect(db_path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT 1 FROM sessions WHERE id = ?",
                (session_id,),
            ).fetchone()
            if row is None:
                conn.rollback()
                raise SessionNotFoundError("Session not found")
            if _session_messages_table_exists(conn):
                conn.execute(
                    "DELETE FROM session_messages WHERE session_id = ?", (session_id,)
                )
            if _chat_artifacts_table_exists(conn):
                conn.execute(
                    "DELETE FROM chat_artifacts WHERE session_id = ?", (session_id,)
                )
            conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            conn.commit()
    except SessionNotFoundError:
        raise
    except Exception as exc:
        _raise_persistence_write_error(
            operation="session_delete",
            db_path=db_path,
            exc=exc,
            session_id=session_id,
        )


def delete_all_sessions(
    *,
    db_path: Path,
    owner_filter: str | None = None,
    tenant_filter: str | None = None,
) -> None:
    """Remove rows from ``sessions`` (and ``session_messages``); ``conversations`` audit rows remain."""
    try:
        with sqlite3.connect(db_path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            if (
                owner_filter is not None or tenant_filter is not None
            ) and _sessions_has_owner_id_column(conn):
                clauses: list[str] = []
                params: list[str] = []
                if owner_filter is not None:
                    clauses.append("owner_id = ?")
                    params.append(owner_filter)
                if tenant_filter is not None and _sessions_has_tenant_columns(conn):
                    clauses.append("tenant_id = ?")
                    params.append(tenant_filter)
                where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
                ids = [
                    str(r[0])
                    for r in conn.execute(
                        f"SELECT id FROM sessions {where_sql}",
                        tuple(params),
                    ).fetchall()
                ]
                if _session_messages_table_exists(conn):
                    for sid in ids:
                        conn.execute(
                            "DELETE FROM session_messages WHERE session_id = ?", (sid,)
                        )
                if _chat_artifacts_table_exists(conn):
                    artifact_clauses = list(clauses)
                    artifact_params = list(params)
                    artifact_where = (
                        f"WHERE {' AND '.join(artifact_clauses)}"
                        if artifact_clauses
                        else ""
                    )
                    conn.execute(
                        f"DELETE FROM chat_artifacts {artifact_where}",
                        tuple(artifact_params),
                    )
                conn.execute(f"DELETE FROM sessions {where_sql}", tuple(params))
            else:
                if _session_messages_table_exists(conn):
                    conn.execute("DELETE FROM session_messages")
                if _chat_artifacts_table_exists(conn):
                    conn.execute("DELETE FROM chat_artifacts")
                conn.execute("DELETE FROM sessions")
            conn.commit()
    except Exception as exc:
        _raise_persistence_write_error(
            operation="session_delete_all",
            db_path=db_path,
            exc=exc,
        )


def create_chat_artifact(
    *,
    db_path: Path,
    artifact_id: str,
    session_id: str,
    owner_id: str,
    tenant_id: str,
    principal_id: str,
    filename: str,
    mime_type: str,
    byte_size: int,
    storage_path: str,
    source_message_index: int,
    created_at: str,
) -> None:
    """Persist one generated chat artifact."""
    try:
        with sqlite3.connect(db_path) as conn:
            if _chat_artifacts_has_tenant_columns(conn):
                conn.execute(
                    """
                    INSERT INTO chat_artifacts
                        (id, session_id, owner_id, tenant_id, principal_id, filename, mime_type, byte_size, storage_path, source_message_index, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        artifact_id,
                        session_id,
                        owner_id,
                        tenant_id,
                        principal_id,
                        filename,
                        mime_type,
                        int(byte_size),
                        storage_path,
                        int(source_message_index),
                        created_at,
                    ),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO chat_artifacts
                        (id, session_id, owner_id, filename, mime_type, byte_size, storage_path, source_message_index, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        artifact_id,
                        session_id,
                        owner_id,
                        filename,
                        mime_type,
                        int(byte_size),
                        storage_path,
                        int(source_message_index),
                        created_at,
                    ),
                )
    except Exception as exc:
        _raise_persistence_write_error(
            operation="chat_artifact_create",
            db_path=db_path,
            exc=exc,
            artifact_id=artifact_id,
        )


def get_chat_artifact(*, db_path: Path, artifact_id: str) -> dict[str, Any] | None:
    """Return one persisted chat artifact metadata row."""
    try:
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                f"""
                SELECT {"id, session_id, owner_id, tenant_id, principal_id, filename, mime_type, byte_size, storage_path, source_message_index, created_at" if _chat_artifacts_has_tenant_columns(conn) else "id, session_id, owner_id, filename, mime_type, byte_size, storage_path, source_message_index, created_at"}
                FROM chat_artifacts
                WHERE id = ?
                """,
                (artifact_id,),
            ).fetchone()
        return dict(row) if row is not None else None
    except Exception:
        logger.exception(
            "Failed to fetch chat artifact %s from %s", artifact_id, db_path
        )
        return None
