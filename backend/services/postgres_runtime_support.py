"""Shared Postgres helpers for Phase 16D runtime metadata persistence."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from alembic import command
from alembic.config import Config
import psycopg
from psycopg import sql
from psycopg.rows import dict_row

from backend.services.runtime_metadata_inventory import (
    RUNTIME_METADATA_TABLES,
    runtime_metadata_order_by,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_ALEMBIC_INI_PATH = _REPO_ROOT / "alembic.ini"
_ALEMBIC_SCRIPT_LOCATION = _REPO_ROOT / "backend" / "alembic"


def postgres_connect(dsn: str) -> psycopg.Connection[Any]:
    return psycopg.connect(dsn, row_factory=dict_row)


def sqlalchemy_postgres_url(dsn: str) -> str:
    if dsn.startswith("postgresql+psycopg://"):
        return dsn
    if dsn.startswith("postgresql://"):
        return "postgresql+psycopg://" + dsn[len("postgresql://") :]
    if dsn.startswith("postgres://"):
        return "postgresql+psycopg://" + dsn[len("postgres://") :]
    return dsn


def run_postgres_runtime_migrations(dsn: str) -> None:
    config = Config(str(_ALEMBIC_INI_PATH))
    config.set_main_option("script_location", str(_ALEMBIC_SCRIPT_LOCATION))
    config.set_main_option("sqlalchemy.url", sqlalchemy_postgres_url(dsn))
    command.upgrade(config, "head")


def current_postgres_alembic_revision(dsn: str) -> str | None:
    with postgres_connect(dsn) as conn:
        row = conn.execute("SELECT version_num FROM alembic_version").fetchone()
    if row is None:
        return None
    return str(row["version_num"])


def ensure_postgres_runtime_metadata_tables_exist(
    conn: psycopg.Connection[Any],
) -> None:
    rows = conn.execute(
        """
        SELECT tablename
        FROM pg_tables
        WHERE schemaname = current_schema()
        """
    ).fetchall()
    existing = {str(row["tablename"]) for row in rows}
    missing = [
        table_name
        for table_name in RUNTIME_METADATA_TABLES
        if table_name not in existing
    ]
    if missing:
        joined = ", ".join(missing)
        raise RuntimeError(
            f"Postgres runtime metadata inventory is incomplete; missing tables: {joined}"
        )


def fetch_postgres_table_rows(
    conn: psycopg.Connection[Any],
    table_name: str,
) -> list[dict[str, Any]]:
    rows = conn.execute(
        sql.SQL("SELECT * FROM {} ORDER BY {}").format(
            sql.Identifier(table_name),
            sql.SQL(runtime_metadata_order_by(table_name)),
        )
    ).fetchall()
    return [dict(row) for row in rows]


def reset_postgres_identity_column(
    conn: psycopg.Connection[Any],
    *,
    table_name: str,
    column_name: str,
) -> None:
    row = conn.execute(
        sql.SQL("SELECT COALESCE(MAX({}), 0) AS max_id FROM {}").format(
            sql.Identifier(column_name),
            sql.Identifier(table_name),
        )
    ).fetchone()
    next_value = int(row["max_id"]) + 1 if row is not None else 1
    conn.execute(
        sql.SQL("ALTER TABLE {} ALTER COLUMN {} RESTART WITH {}").format(
            sql.Identifier(table_name),
            sql.Identifier(column_name),
            sql.Literal(next_value),
        )
    )


def lock_parent_row(
    conn: psycopg.Connection[Any],
    *,
    table_name: str,
    key_column: str,
    key_value: str,
) -> None:
    conn.execute(
        sql.SQL("SELECT 1 FROM {} WHERE {} = %s FOR UPDATE").format(
            sql.Identifier(table_name),
            sql.Identifier(key_column),
        ),
        (key_value,),
    ).fetchone()


def next_scoped_sequence(
    conn: psycopg.Connection[Any],
    *,
    table_name: str,
    scope_column: str,
    scope_value: str,
) -> int:
    row = conn.execute(
        sql.SQL(
            "SELECT COALESCE(MAX(seq), 0) + 1 AS next_seq FROM {} WHERE {} = %s"
        ).format(
            sql.Identifier(table_name),
            sql.Identifier(scope_column),
        ),
        (scope_value,),
    ).fetchone()
    return int(row["next_seq"]) if row is not None else 1
