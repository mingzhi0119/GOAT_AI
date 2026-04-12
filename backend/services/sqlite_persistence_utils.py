from __future__ import annotations

import json
import sqlite3

from backend.services.exceptions import PersistenceReadError, PersistenceWriteError


def raise_read_error(operation: str, exc: Exception) -> None:
    raise PersistenceReadError(f"Failed to {operation.replace('_', ' ')}.") from exc


def raise_write_error(operation: str, exc: Exception) -> None:
    raise PersistenceWriteError(f"Failed to {operation.replace('_', ' ')}.") from exc


def encode_json(value: object, *, sort_keys: bool = False) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=sort_keys)


def decode_string_list(raw: object) -> list[str]:
    if not isinstance(raw, str) or not raw.strip():
        return []
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []
    return [str(item) for item in parsed if isinstance(item, str)]


def decode_object_list(raw: object) -> list[dict[str, object]] | None:
    if not isinstance(raw, str) or not raw.strip():
        return None
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, list):
        return None
    out: list[dict[str, object]] = []
    for item in parsed:
        if isinstance(item, dict):
            out.append(item)
    return out


def decode_object(raw: object) -> dict[str, object] | None:
    if not isinstance(raw, str) or not raw.strip():
        return None
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict):
        return None
    return parsed


def decode_files(raw: object) -> list[dict[str, object]]:
    if not isinstance(raw, str) or not raw.strip():
        return []
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []
    out: list[dict[str, object]] = []
    for item in parsed:
        if isinstance(item, dict):
            out.append({str(key): value for key, value in item.items()})
    return out


def next_scoped_sequence(
    conn: sqlite3.Connection,
    *,
    table: str,
    scope_column: str,
    scope_value: str,
) -> int:
    query = f"SELECT COALESCE(MAX(seq), 0) + 1 FROM {table} WHERE {scope_column} = ?"
    row = conn.execute(query, (scope_value,)).fetchone()
    return int(row[0]) if row is not None else 1
