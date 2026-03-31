"""Conversation logging — writes Q&A pairs to a local SQLite database.

Each successful (or partial) chat completion is appended as one row in the
``conversations`` table.  Errors inside this module are logged and swallowed
so they never interrupt a live SSE stream.

WAL journal mode is enabled at init time, making concurrent writes from
multiple uvicorn workers safe without extra locking.
"""
from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_DDL = """
CREATE TABLE IF NOT EXISTS conversations (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at         TEXT    NOT NULL,
    ip                 TEXT    NOT NULL,
    model              TEXT    NOT NULL,
    turn_count         INTEGER NOT NULL,
    user_message       TEXT    NOT NULL,
    assistant_response TEXT    NOT NULL,
    response_ms        INTEGER,
    user_name          TEXT    NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS sessions (
    id         TEXT PRIMARY KEY,
    title      TEXT NOT NULL DEFAULT '',
    model      TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    messages   TEXT NOT NULL DEFAULT '[]'
);
"""


def init_db(db_path: Path) -> None:
    """Create the conversations table if it does not already exist.

    Also applies incremental schema migrations (idempotent).
    Called once at application startup; safe to call multiple times.
    """
    try:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(db_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.executescript(_DDL)
            # Migration: add user_name column to existing databases
            try:
                conn.execute(
                    "ALTER TABLE conversations ADD COLUMN user_name TEXT NOT NULL DEFAULT ''"
                )
            except sqlite3.OperationalError:
                pass  # column already exists
            # Migration: add session_id column to existing databases
            try:
                conn.execute("ALTER TABLE conversations ADD COLUMN session_id TEXT")
            except sqlite3.OperationalError:
                pass  # column already exists
        logger.info("Chat log DB ready: %s", db_path)
    except Exception:
        logger.exception("Failed to initialise chat log DB at %s", db_path)


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
        logger.exception("Failed to log conversation to %s", db_path)


def upsert_session(
    *,
    db_path: Path,
    session_id: str,
    title: str,
    model: str,
    messages: list[dict[str, str]],
    created_at: str,
    updated_at: str,
) -> None:
    """Insert or update a persisted chat session with full message history."""
    try:
        payload = json.dumps(messages, ensure_ascii=False)
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                """
                INSERT INTO sessions (id, title, model, created_at, updated_at, messages)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    title=excluded.title,
                    model=excluded.model,
                    updated_at=excluded.updated_at,
                    messages=excluded.messages
                """,
                (session_id, title, model, created_at, updated_at, payload),
            )
    except Exception:
        logger.exception("Failed to upsert session %s in %s", session_id, db_path)


def list_sessions(*, db_path: Path) -> list[dict[str, Any]]:
    """Return lightweight session metadata for sidebar listing."""
    try:
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT id, title, model, created_at, updated_at
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
                SELECT id, title, model, created_at, updated_at, messages
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
        item["messages"] = parsed if isinstance(parsed, list) else []
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
        logger.exception("Failed to delete session %s from %s", session_id, db_path)


def delete_all_sessions(*, db_path: Path) -> None:
    """Remove all rows from ``sessions`` only; ``conversations`` audit rows remain."""
    try:
        with sqlite3.connect(db_path) as conn:
            conn.execute("DELETE FROM sessions")
    except Exception:
        logger.exception("Failed to delete all sessions from %s", db_path)
