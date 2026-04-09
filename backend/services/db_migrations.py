"""Apply numbered SQL migrations from ``backend/migrations`` in order.

Each file is recorded in ``schema_migrations`` with a SHA-256 checksum of file bytes.
Additive ``ALTER TABLE`` steps are idempotent when SQLite reports a duplicate column.
"""

from __future__ import annotations

import hashlib
import logging
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

_MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"
_MIGRATION_NAME = re.compile(r"^(\d{3})_.+\.sql$")
_FIRST_MIGRATION_ID = "001_schema_migrations"


def _list_migration_files() -> list[Path]:
    if not _MIGRATIONS_DIR.is_dir():
        return []
    files: list[Path] = []
    for path in sorted(_MIGRATIONS_DIR.iterdir()):
        if path.is_file() and _MIGRATION_NAME.match(path.name):
            files.append(path)
    return files


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (name,),
    ).fetchone()
    return row is not None


def _file_checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _is_duplicate_column_error(exc: sqlite3.OperationalError) -> bool:
    return "duplicate column name" in str(exc).lower()


def _execute_script(conn: sqlite3.Connection, sql: str, migration_id: str) -> None:
    try:
        conn.executescript(sql)
    except sqlite3.OperationalError as exc:
        if _is_duplicate_column_error(exc):
            logger.info(
                "Migration %s: column already present, treating as applied",
                migration_id,
            )
            return
        raise


def apply_migrations(db_path: Path) -> None:
    """Create ``db_path`` parent dirs, enable WAL, apply all pending ``NNN_*.sql`` migrations."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    files = _list_migration_files()
    if not files:
        logger.warning("No SQL migrations found under %s", _MIGRATIONS_DIR)
        return

    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")

        for path in files:
            migration_id = path.stem
            checksum = _file_checksum(path)

            if not _table_exists(conn, "schema_migrations"):
                if migration_id != _FIRST_MIGRATION_ID:
                    msg = (
                        f"Database {db_path} has no schema_migrations table but first migration "
                        f"file is {migration_id!r}; expected {_FIRST_MIGRATION_ID!r}."
                    )
                    raise RuntimeError(msg)

            stored_checksum: str | None = None
            if _table_exists(conn, "schema_migrations"):
                row = conn.execute(
                    "SELECT checksum FROM schema_migrations WHERE id = ?",
                    (migration_id,),
                ).fetchone()
                if row is not None:
                    stored_checksum = str(row[0])

            if stored_checksum is not None:
                if stored_checksum != checksum:
                    raise RuntimeError(
                        f"Migration {migration_id} was applied with checksum {stored_checksum!r} "
                        f"but file on disk hashes to {checksum!r}; refuse to start."
                    )
                continue

            sql_text = path.read_text(encoding="utf-8")
            applied_at = datetime.now(timezone.utc).isoformat()
            logger.info("Applying migration %s", migration_id)
            try:
                conn.execute("BEGIN IMMEDIATE;")
                _execute_script(conn, sql_text, migration_id)
                conn.execute(
                    "INSERT INTO schema_migrations (id, applied_at, checksum) VALUES (?, ?, ?)",
                    (migration_id, applied_at, checksum),
                )
                conn.execute("COMMIT;")
            except Exception:
                conn.execute("ROLLBACK;")
                logger.exception("Migration %s failed", migration_id)
                raise

        try:
            conn.execute("PRAGMA wal_checkpoint(FULL);")
        except sqlite3.OperationalError:
            pass
