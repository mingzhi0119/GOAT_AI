"""Deterministic SQLite runtime-metadata snapshot export for Phase 16D parity work."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

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
