"""Deterministic SQLite runtime-metadata snapshot export for Phase 16D parity work."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from psycopg import sql

from backend.services.postgres_runtime_support import (
    ensure_postgres_runtime_metadata_tables_exist,
    fetch_postgres_table_rows,
    postgres_connect,
    reset_postgres_identity_column,
)
from backend.services.runtime_metadata_inventory import (
    RUNTIME_METADATA_TABLES,
    runtime_metadata_order_by,
)

SNAPSHOT_FORMAT_VERSION = 1


def export_sqlite_runtime_metadata_snapshot(db_path: Path) -> dict[str, Any]:
    """Return a deterministic JSON-serializable snapshot of governed metadata tables."""
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        _ensure_runtime_metadata_tables_exist(conn)
        tables = {
            table_name: _fetch_table_rows(conn, table_name)
            for table_name in RUNTIME_METADATA_TABLES
        }
    return {
        "snapshot_format_version": SNAPSHOT_FORMAT_VERSION,
        "source_backend": "sqlite",
        "tables": tables,
    }


def write_sqlite_runtime_metadata_snapshot(*, db_path: Path, out_path: Path) -> Path:
    """Write a deterministic runtime-metadata snapshot JSON file."""
    snapshot = export_sqlite_runtime_metadata_snapshot(db_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return out_path


def export_postgres_runtime_metadata_snapshot(dsn: str) -> dict[str, Any]:
    """Return a deterministic JSON-serializable snapshot of governed Postgres tables."""
    with postgres_connect(dsn) as conn:
        ensure_postgres_runtime_metadata_tables_exist(conn)
        tables = {
            table_name: fetch_postgres_table_rows(conn, table_name)
            for table_name in RUNTIME_METADATA_TABLES
        }
    return {
        "snapshot_format_version": SNAPSHOT_FORMAT_VERSION,
        "source_backend": "postgres",
        "tables": tables,
    }


def read_runtime_metadata_snapshot(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def import_runtime_metadata_snapshot_to_postgres(
    *,
    snapshot: dict[str, Any],
    dsn: str,
) -> None:
    if int(snapshot.get("snapshot_format_version", 0)) != SNAPSHOT_FORMAT_VERSION:
        raise RuntimeError("Unsupported runtime metadata snapshot format version.")
    tables = snapshot.get("tables")
    if not isinstance(tables, dict):
        raise RuntimeError("Runtime metadata snapshot is missing table data.")

    with postgres_connect(dsn) as conn:
        ensure_postgres_runtime_metadata_tables_exist(conn)
        with conn.transaction():
            _ensure_postgres_runtime_tables_are_empty(conn)
            for table_name in RUNTIME_METADATA_TABLES:
                raw_rows = tables.get(table_name, [])
                if not isinstance(raw_rows, list):
                    raise RuntimeError(f"Snapshot table {table_name} must be a list.")
                if not raw_rows:
                    continue
                _insert_rows_into_postgres_table(
                    conn,
                    table_name=table_name,
                    rows=raw_rows,
                )
            for table_name in ("conversations", "workbench_task_events"):
                reset_postgres_identity_column(
                    conn,
                    table_name=table_name,
                    column_name="id",
                )


def compare_runtime_metadata_snapshot_to_postgres(
    *,
    snapshot: dict[str, Any],
    dsn: str,
) -> list[str]:
    expected_tables = snapshot.get("tables")
    if not isinstance(expected_tables, dict):
        raise RuntimeError("Runtime metadata snapshot is missing table data.")
    actual_snapshot = export_postgres_runtime_metadata_snapshot(dsn)
    actual_tables = actual_snapshot["tables"]
    mismatches: list[str] = []
    for table_name in RUNTIME_METADATA_TABLES:
        expected_rows = expected_tables.get(table_name, [])
        actual_rows = actual_tables.get(table_name, [])
        if expected_rows != actual_rows:
            mismatches.append(
                f"{table_name}: expected {len(expected_rows)} rows, got {len(actual_rows)} rows"
            )
    return mismatches


def _ensure_runtime_metadata_tables_exist(conn: sqlite3.Connection) -> None:
    existing = {
        str(row[0])
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    missing = [
        table_name
        for table_name in RUNTIME_METADATA_TABLES
        if table_name not in existing
    ]
    if missing:
        joined = ", ".join(missing)
        raise RuntimeError(
            f"SQLite runtime metadata inventory is incomplete; missing tables: {joined}"
        )


def _fetch_table_rows(
    conn: sqlite3.Connection,
    table_name: str,
) -> list[dict[str, Any]]:
    rows = conn.execute(
        f"SELECT * FROM {table_name} ORDER BY {runtime_metadata_order_by(table_name)}"
    ).fetchall()
    return [dict(row) for row in rows]


def _ensure_postgres_runtime_tables_are_empty(conn) -> None:
    populated: list[str] = []
    for table_name in RUNTIME_METADATA_TABLES:
        row = conn.execute(
            sql.SQL("SELECT 1 FROM {} LIMIT 1").format(sql.Identifier(table_name))
        ).fetchone()
        if row is not None:
            populated.append(table_name)
    if populated:
        raise RuntimeError(
            "Postgres runtime metadata import requires an empty target; populated tables: "
            + ", ".join(populated)
        )


def _insert_rows_into_postgres_table(
    conn,
    *,
    table_name: str,
    rows: list[dict[str, Any]],
) -> None:
    columns = list(rows[0].keys())
    placeholders = sql.SQL(", ").join(sql.Placeholder() for _ in columns)
    statement = sql.SQL("INSERT INTO {} ({}) VALUES ({})").format(
        sql.Identifier(table_name),
        sql.SQL(", ").join(sql.Identifier(column) for column in columns),
        placeholders,
    )
    for row in rows:
        conn.execute(statement, tuple(row[column] for column in columns))
