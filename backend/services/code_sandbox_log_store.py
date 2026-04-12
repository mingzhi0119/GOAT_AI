from __future__ import annotations

import sqlite3
from pathlib import Path

from backend.services.code_sandbox_runtime import (
    CodeSandboxLogChunkRecord,
    LogStreamName,
)
from backend.services.sqlite_persistence_utils import (
    encode_json,
    next_scoped_sequence,
    raise_read_error,
    raise_write_error,
)


class SQLiteCodeSandboxLogStore:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path

    def append_log_chunk(
        self,
        execution_id: str,
        *,
        created_at: str,
        stream_name: LogStreamName,
        chunk_text: str,
    ) -> int:
        try:
            with sqlite3.connect(self._db_path) as conn:
                conn.execute("BEGIN IMMEDIATE")
                next_seq = self.append_log_chunk_in_transaction(
                    conn,
                    execution_id,
                    created_at=created_at,
                    stream_name=stream_name,
                    chunk_text=chunk_text,
                )
                conn.commit()
                return next_seq
        except Exception as exc:
            raise_write_error("code_sandbox_log_chunk_append", exc)

    def list_log_chunks(
        self, execution_id: str, *, after_sequence: int = 0
    ) -> list[CodeSandboxLogChunkRecord]:
        try:
            with sqlite3.connect(self._db_path) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(
                    """
                    SELECT execution_id, seq, stream_name, created_at, chunk_text
                    FROM code_sandbox_execution_logs
                    WHERE execution_id = ? AND seq > ?
                    ORDER BY seq ASC
                    """,
                    (execution_id, after_sequence),
                ).fetchall()
        except Exception as exc:
            raise_read_error("code_sandbox_log_chunks_list", exc)
        return [
            CodeSandboxLogChunkRecord(
                execution_id=str(row["execution_id"]),
                sequence=int(row["seq"]),
                stream_name=str(row["stream_name"]),
                created_at=str(row["created_at"]),
                chunk_text=str(row["chunk_text"]),
            )
            for row in rows
        ]

    def append_log_chunk_in_transaction(
        self,
        conn: sqlite3.Connection,
        execution_id: str,
        *,
        created_at: str,
        stream_name: LogStreamName,
        chunk_text: str,
    ) -> int:
        next_seq = next_scoped_sequence(
            conn,
            table="code_sandbox_execution_logs",
            scope_column="execution_id",
            scope_value=execution_id,
        )
        conn.execute(
            """
            INSERT INTO code_sandbox_execution_logs (
                execution_id,
                seq,
                stream_name,
                created_at,
                chunk_text
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (execution_id, next_seq, stream_name, created_at, chunk_text),
        )
        conn.execute(
            f"""
            UPDATE code_sandbox_executions
            SET updated_at = ?,
                last_log_seq = ?,
                {stream_name} = COALESCE({stream_name}, '') || ?
            WHERE id = ?
            """,
            (created_at, next_seq, chunk_text, execution_id),
        )
        self._append_log_event(
            conn,
            execution_id=execution_id,
            stream_name=stream_name,
            created_at=created_at,
            sequence=next_seq,
            chunk_text=chunk_text,
        )
        return next_seq

    def _append_log_event(
        self,
        conn: sqlite3.Connection,
        *,
        execution_id: str,
        stream_name: LogStreamName,
        created_at: str,
        sequence: int,
        chunk_text: str,
    ) -> None:
        conn.execute(
            """
            INSERT INTO code_sandbox_execution_events (
                execution_id,
                seq,
                event_type,
                created_at,
                status,
                message,
                metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                execution_id,
                next_scoped_sequence(
                    conn,
                    table="code_sandbox_execution_events",
                    scope_column="execution_id",
                    scope_value=execution_id,
                ),
                f"execution.log.{stream_name}",
                created_at,
                "running",
                None,
                encode_json(
                    {
                        "log_sequence": sequence,
                        "stream_name": stream_name,
                        "byte_size": len(chunk_text.encode("utf-8")),
                    },
                    sort_keys=True,
                ),
            ),
        )
