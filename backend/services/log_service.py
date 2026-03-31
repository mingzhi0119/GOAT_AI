"""Conversation logging — writes Q&A pairs to a local SQLite database.

Each successful (or partial) chat completion is appended as one row in the
``conversations`` table.  Errors inside this module are logged and swallowed
so they never interrupt a live SSE stream.

WAL journal mode is enabled at init time, making concurrent writes from
multiple uvicorn workers safe without extra locking.
"""
from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

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
                    (created_at, ip, model, turn_count, user_message, assistant_response, response_ms, user_name)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (created_at, ip, model, turn_count, user_message, assistant_response, response_ms, user_name),
            )
    except Exception:
        logger.exception("Failed to log conversation to %s", db_path)
