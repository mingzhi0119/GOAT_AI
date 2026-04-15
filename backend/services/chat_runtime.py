"""Typed runtime interfaces and adapters for chat/session infrastructure."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

from backend.domain.resource_ownership import (
    PersistedResourceOwnership,
    ownership_from_fields,
)
from backend.services.artifact_service import PersistedArtifactRecord
from backend.services import log_service
from backend.services.exceptions import (
    PersistenceReadError,
    PersistenceWriteError,
    SessionNotFoundError,
)
from backend.services.postgres_runtime_support import postgres_connect
from backend.services.session_message_codec import decode_session_payload
from goat_ai.llm.ollama_client import LLMClient


@dataclass(frozen=True, kw_only=True)
class SessionSummaryRecord:
    """Typed session summary returned by the history repository."""

    id: str
    title: str
    model: str
    schema_version: int
    created_at: str
    updated_at: str
    owner_id: str
    tenant_id: str = "tenant:default"
    principal_id: str = ""

    @property
    def ownership(self) -> PersistedResourceOwnership:
        return ownership_from_fields(
            owner_id=self.owner_id,
            tenant_id=self.tenant_id,
            principal_id=self.principal_id,
        )


@dataclass(frozen=True, kw_only=True)
class SessionDetailRecord(SessionSummaryRecord):
    """Typed session detail returned by the history repository."""

    messages: list[dict[str, Any]]
    chart_spec: dict[str, object] | None = None
    file_context_prompt: str | None = None
    knowledge_documents: list[dict[str, str]] | None = None
    chart_data_source: str | None = None
    persona_snapshot: dict[str, str] | None = None


@dataclass(frozen=True, kw_only=True)
class SessionUpsertPayload:
    """Payload required to persist a chat session snapshot."""

    session_id: str
    title: str
    model: str
    schema_version: int
    payload: dict[str, object]
    created_at: str
    updated_at: str
    owner_id: str = ""
    tenant_id: str = "tenant:default"
    principal_id: str = ""

    @property
    def ownership(self) -> PersistedResourceOwnership:
        return ownership_from_fields(
            owner_id=self.owner_id,
            tenant_id=self.tenant_id,
            principal_id=self.principal_id,
        )


@dataclass(frozen=True)
class ConversationLogEntry:
    """One completed chat turn to record in the conversation audit log."""

    ip: str
    model: str
    turn_count: int
    user_message: str
    assistant_response: str
    response_ms: int | None
    user_name: str = ""
    session_id: str | None = None


class SessionRepository(Protocol):
    """Persistence boundary for stored session snapshots."""

    def list_sessions(
        self,
        owner_filter: str | None = None,
        *,
        tenant_filter: str | None = None,
    ) -> list[SessionSummaryRecord]: ...

    def get_session(self, session_id: str) -> SessionDetailRecord | None: ...

    def upsert_session(self, payload: SessionUpsertPayload) -> None: ...

    def rename_session(self, session_id: str, title: str) -> None: ...

    def delete_session(self, session_id: str) -> None: ...

    def delete_all_sessions(
        self,
        owner_filter: str | None = None,
        *,
        tenant_filter: str | None = None,
    ) -> None: ...

    def create_chat_artifact(self, record: PersistedArtifactRecord) -> None: ...

    def get_chat_artifact(self, artifact_id: str) -> PersistedArtifactRecord | None: ...


class ConversationLogger(Protocol):
    """Persistence boundary for append-only conversation audit logs."""

    def log(self, entry: ConversationLogEntry) -> None: ...


class TitleGenerator(Protocol):
    """Infrastructure boundary for optional LLM-generated session titles."""

    def generate_title(
        self,
        *,
        model: str,
        user_text: str,
        assistant_text: str,
    ) -> str | None: ...


class SQLiteSessionRepository:
    """SQLite-backed implementation of SessionRepository."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path

    def list_sessions(
        self,
        owner_filter: str | None = None,
        *,
        tenant_filter: str | None = None,
    ) -> list[SessionSummaryRecord]:
        rows = log_service.list_sessions(
            db_path=self._db_path,
            owner_filter=owner_filter,
            tenant_filter=tenant_filter,
        )
        return [
            SessionSummaryRecord(
                id=str(row["id"]),
                title=str(row["title"]),
                model=str(row["model"]),
                schema_version=int(row.get("schema_version", 1)),
                created_at=str(row["created_at"]),
                updated_at=str(row["updated_at"]),
                owner_id=str(row.get("owner_id", "")),
                tenant_id=str(row.get("tenant_id", "tenant:default")),
                principal_id=str(row.get("principal_id", "")),
            )
            for row in rows
        ]

    def get_session(self, session_id: str) -> SessionDetailRecord | None:
        row = log_service.get_session(db_path=self._db_path, session_id=session_id)
        if row is None:
            return None
        decoded = decode_session_payload(row.get("messages", []))
        return SessionDetailRecord(
            id=str(row["id"]),
            title=str(row["title"]),
            model=str(row["model"]),
            schema_version=int(row.get("schema_version", 1)),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
            owner_id=str(row.get("owner_id", "")),
            tenant_id=str(row.get("tenant_id", "tenant:default")),
            principal_id=str(row.get("principal_id", "")),
            messages=decoded.messages,
            chart_spec=decoded.chart_spec,
            file_context_prompt=decoded.file_context_prompt,
            knowledge_documents=decoded.knowledge_documents,
            chart_data_source=decoded.chart_data_source,
            persona_snapshot=decoded.persona_snapshot,
        )

    def upsert_session(self, payload: SessionUpsertPayload) -> None:
        log_service.upsert_session(
            db_path=self._db_path,
            session_id=payload.session_id,
            title=payload.title,
            model=payload.model,
            schema_version=payload.schema_version,
            payload=payload.payload,
            created_at=payload.created_at,
            updated_at=payload.updated_at,
            owner_id=payload.owner_id,
            tenant_id=payload.tenant_id,
            principal_id=payload.principal_id,
        )

    def rename_session(self, session_id: str, title: str) -> None:
        log_service.rename_session_title(
            db_path=self._db_path,
            session_id=session_id,
            title=title,
        )

    def delete_session(self, session_id: str) -> None:
        log_service.delete_session(db_path=self._db_path, session_id=session_id)

    def delete_all_sessions(
        self,
        owner_filter: str | None = None,
        *,
        tenant_filter: str | None = None,
    ) -> None:
        log_service.delete_all_sessions(
            db_path=self._db_path,
            owner_filter=owner_filter,
            tenant_filter=tenant_filter,
        )

    def create_chat_artifact(self, record: PersistedArtifactRecord) -> None:
        log_service.create_chat_artifact(
            db_path=self._db_path,
            artifact_id=record.id,
            session_id=record.session_id,
            owner_id=record.owner_id,
            tenant_id=record.tenant_id,
            principal_id=record.principal_id,
            filename=record.filename,
            mime_type=record.mime_type,
            byte_size=record.byte_size,
            storage_path=record.storage_path,
            storage_key=record.storage_key,
            source_message_index=record.source_message_index,
            created_at=record.created_at,
        )

    def get_chat_artifact(self, artifact_id: str) -> PersistedArtifactRecord | None:
        row = log_service.get_chat_artifact(
            db_path=self._db_path, artifact_id=artifact_id
        )
        if row is None:
            return None
        return PersistedArtifactRecord(
            id=str(row["id"]),
            session_id=str(row["session_id"]),
            owner_id=str(row.get("owner_id", "")),
            tenant_id=str(row.get("tenant_id", "tenant:default")),
            principal_id=str(row.get("principal_id", "")),
            filename=str(row["filename"]),
            mime_type=str(row["mime_type"]),
            byte_size=int(row["byte_size"]),
            storage_path=str(row["storage_path"]),
            storage_key=str(row.get("storage_key", "")),
            source_message_index=int(row.get("source_message_index", 0)),
            created_at=str(row["created_at"]),
        )


class SQLiteConversationLogger:
    """SQLite-backed implementation of ConversationLogger."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path

    def log(self, entry: ConversationLogEntry) -> None:
        log_service.log_conversation(
            db_path=self._db_path,
            ip=entry.ip,
            model=entry.model,
            turn_count=entry.turn_count,
            user_message=entry.user_message,
            assistant_response=entry.assistant_response,
            response_ms=entry.response_ms,
            user_name=entry.user_name,
            session_id=entry.session_id,
        )


class PostgresSessionRepository:
    """Postgres-backed implementation of SessionRepository."""

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn

    def list_sessions(
        self,
        owner_filter: str | None = None,
        *,
        tenant_filter: str | None = None,
    ) -> list[SessionSummaryRecord]:
        clauses: list[str] = []
        params: list[str] = []
        if owner_filter is not None:
            clauses.append("owner_id = %s")
            params.append(owner_filter)
        if tenant_filter is not None:
            clauses.append("tenant_id = %s")
            params.append(tenant_filter)
        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        try:
            with postgres_connect(self._dsn) as conn:
                rows = conn.execute(
                    f"""
                    SELECT id, title, model, schema_version, created_at, updated_at, owner_id, tenant_id, principal_id
                    FROM sessions
                    {where_sql}
                    ORDER BY updated_at DESC
                    """,
                    tuple(params),
                ).fetchall()
        except Exception as exc:
            raise PersistenceReadError("Failed to session list.") from exc
        return [
            SessionSummaryRecord(
                id=str(row["id"]),
                title=str(row["title"]),
                model=str(row["model"]),
                schema_version=int(row.get("schema_version", 1)),
                created_at=str(row["created_at"]),
                updated_at=str(row["updated_at"]),
                owner_id=str(row.get("owner_id", "")),
                tenant_id=str(row.get("tenant_id", "tenant:default")),
                principal_id=str(row.get("principal_id", "")),
            )
            for row in rows
        ]

    def get_session(self, session_id: str) -> SessionDetailRecord | None:
        try:
            with postgres_connect(self._dsn) as conn:
                row = conn.execute(
                    """
                    SELECT id, title, model, schema_version, created_at, updated_at, messages, owner_id, tenant_id, principal_id
                    FROM sessions
                    WHERE id = %s
                    """,
                    (session_id,),
                ).fetchone()
                if row is None:
                    return None
                messages_value = json.loads(str(row["messages"]))
                normalized_rows = conn.execute(
                    """
                    SELECT role, content, image_attachment_ids, artifacts_json
                    FROM session_messages
                    WHERE session_id = %s
                    ORDER BY seq ASC
                    """,
                    (session_id,),
                ).fetchall()
        except Exception as exc:
            raise PersistenceReadError("Failed to session get.") from exc

        normalized: list[dict[str, Any]] | None = None
        if normalized_rows:
            normalized = []
            for msg_row in normalized_rows:
                item: dict[str, Any] = {
                    "role": str(msg_row["role"]),
                    "content": str(msg_row["content"]),
                }
                ids_raw = msg_row["image_attachment_ids"]
                if isinstance(ids_raw, str) and ids_raw.strip():
                    parsed_ids = json.loads(ids_raw)
                    if isinstance(parsed_ids, list) and parsed_ids:
                        item["image_attachment_ids"] = parsed_ids
                artifacts_raw = msg_row["artifacts_json"]
                if isinstance(artifacts_raw, str) and artifacts_raw.strip():
                    parsed_artifacts = json.loads(artifacts_raw)
                    if isinstance(parsed_artifacts, list) and parsed_artifacts:
                        item["artifacts"] = parsed_artifacts
                normalized.append(item)
        merged_messages = (
            log_service._merge_session_messages_into_item(
                messages_value=messages_value,
                normalized=normalized,
            )
            if normalized is not None
            else messages_value
        )
        decoded = decode_session_payload(merged_messages)
        return SessionDetailRecord(
            id=str(row["id"]),
            title=str(row["title"]),
            model=str(row["model"]),
            schema_version=int(row.get("schema_version", 1)),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
            owner_id=str(row.get("owner_id", "")),
            tenant_id=str(row.get("tenant_id", "tenant:default")),
            principal_id=str(row.get("principal_id", "")),
            messages=decoded.messages,
            chart_spec=decoded.chart_spec,
            file_context_prompt=decoded.file_context_prompt,
            knowledge_documents=decoded.knowledge_documents,
            chart_data_source=decoded.chart_data_source,
            persona_snapshot=decoded.persona_snapshot,
        )

    def upsert_session(self, payload: SessionUpsertPayload) -> None:
        try:
            encoded_payload = json.dumps(payload.payload, ensure_ascii=False)
            with postgres_connect(self._dsn) as conn:
                with conn.transaction():
                    conn.execute(
                        """
                        INSERT INTO sessions (id, title, model, schema_version, created_at, updated_at, messages, owner_id, tenant_id, principal_id)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT(id) DO UPDATE SET
                            title = EXCLUDED.title,
                            model = EXCLUDED.model,
                            schema_version = EXCLUDED.schema_version,
                            updated_at = EXCLUDED.updated_at,
                            messages = EXCLUDED.messages,
                            owner_id = EXCLUDED.owner_id,
                            tenant_id = EXCLUDED.tenant_id,
                            principal_id = EXCLUDED.principal_id
                        """,
                        (
                            payload.session_id,
                            payload.title,
                            payload.model,
                            int(payload.schema_version),
                            payload.created_at,
                            payload.updated_at,
                            encoded_payload,
                            payload.owner_id,
                            payload.tenant_id,
                            payload.principal_id,
                        ),
                    )
                    conn.execute(
                        "DELETE FROM session_messages WHERE session_id = %s",
                        (payload.session_id,),
                    )
                    for seq, msg in enumerate(
                        log_service._payload_visible_messages(payload.payload)
                    ):
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
                            INSERT INTO session_messages
                                (session_id, seq, role, content, image_attachment_ids, artifacts_json, created_at)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                            """,
                            (
                                payload.session_id,
                                seq,
                                msg["role"],
                                msg["content"],
                                ids_json,
                                artifacts_json,
                                payload.updated_at,
                            ),
                        )
        except Exception as exc:
            raise PersistenceWriteError("Failed to session upsert.") from exc

    def rename_session(self, session_id: str, title: str) -> None:
        try:
            now_iso = datetime.now(timezone.utc).isoformat()
            with postgres_connect(self._dsn) as conn:
                with conn.transaction():
                    row = conn.execute(
                        """
                        UPDATE sessions
                        SET title = %s, updated_at = %s
                        WHERE id = %s
                        RETURNING id
                        """,
                        (title, now_iso, session_id),
                    ).fetchone()
                    if row is None:
                        raise SessionNotFoundError("Session not found")
        except SessionNotFoundError:
            raise
        except Exception as exc:
            raise PersistenceWriteError("Failed to session rename.") from exc

    def delete_session(self, session_id: str) -> None:
        try:
            with postgres_connect(self._dsn) as conn:
                with conn.transaction():
                    row = conn.execute(
                        "SELECT 1 FROM sessions WHERE id = %s",
                        (session_id,),
                    ).fetchone()
                    if row is None:
                        raise SessionNotFoundError("Session not found")
                    conn.execute(
                        "DELETE FROM session_messages WHERE session_id = %s",
                        (session_id,),
                    )
                    conn.execute(
                        "DELETE FROM chat_artifacts WHERE session_id = %s",
                        (session_id,),
                    )
                    conn.execute("DELETE FROM sessions WHERE id = %s", (session_id,))
        except SessionNotFoundError:
            raise
        except Exception as exc:
            raise PersistenceWriteError("Failed to session delete.") from exc

    def delete_all_sessions(
        self,
        owner_filter: str | None = None,
        *,
        tenant_filter: str | None = None,
    ) -> None:
        clauses: list[str] = []
        params: list[str] = []
        if owner_filter is not None:
            clauses.append("owner_id = %s")
            params.append(owner_filter)
        if tenant_filter is not None:
            clauses.append("tenant_id = %s")
            params.append(tenant_filter)
        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        try:
            with postgres_connect(self._dsn) as conn:
                with conn.transaction():
                    if where_sql:
                        ids = [
                            str(row["id"])
                            for row in conn.execute(
                                f"SELECT id FROM sessions {where_sql}",
                                tuple(params),
                            ).fetchall()
                        ]
                        for session_id in ids:
                            conn.execute(
                                "DELETE FROM session_messages WHERE session_id = %s",
                                (session_id,),
                            )
                            conn.execute(
                                "DELETE FROM chat_artifacts WHERE session_id = %s",
                                (session_id,),
                            )
                        conn.execute(f"DELETE FROM sessions {where_sql}", tuple(params))
                    else:
                        conn.execute("DELETE FROM session_messages")
                        conn.execute("DELETE FROM chat_artifacts")
                        conn.execute("DELETE FROM sessions")
        except Exception as exc:
            raise PersistenceWriteError("Failed to session delete all.") from exc

    def create_chat_artifact(self, record: PersistedArtifactRecord) -> None:
        try:
            with postgres_connect(self._dsn) as conn:
                conn.execute(
                    """
                    INSERT INTO chat_artifacts
                        (id, session_id, owner_id, tenant_id, principal_id, filename, mime_type, byte_size, storage_path, storage_key, source_message_index, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        record.id,
                        record.session_id,
                        record.owner_id,
                        record.tenant_id,
                        record.principal_id,
                        record.filename,
                        record.mime_type,
                        int(record.byte_size),
                        record.storage_path,
                        record.storage_key,
                        int(record.source_message_index),
                        record.created_at,
                    ),
                )
        except Exception as exc:
            raise PersistenceWriteError("Failed to chat artifact create.") from exc

    def get_chat_artifact(self, artifact_id: str) -> PersistedArtifactRecord | None:
        try:
            with postgres_connect(self._dsn) as conn:
                row = conn.execute(
                    """
                    SELECT id, session_id, owner_id, tenant_id, principal_id, filename, mime_type, byte_size, storage_path, storage_key, source_message_index, created_at
                    FROM chat_artifacts
                    WHERE id = %s
                    """,
                    (artifact_id,),
                ).fetchone()
        except Exception as exc:
            raise PersistenceReadError("Failed to chat artifact get.") from exc
        if row is None:
            return None
        return PersistedArtifactRecord(
            id=str(row["id"]),
            session_id=str(row["session_id"]),
            owner_id=str(row.get("owner_id", "")),
            tenant_id=str(row.get("tenant_id", "tenant:default")),
            principal_id=str(row.get("principal_id", "")),
            filename=str(row["filename"]),
            mime_type=str(row["mime_type"]),
            byte_size=int(row["byte_size"]),
            storage_path=str(row["storage_path"]),
            storage_key=str(row.get("storage_key", "")),
            source_message_index=int(row.get("source_message_index", 0)),
            created_at=str(row["created_at"]),
        )


class PostgresConversationLogger:
    """Postgres-backed implementation of ConversationLogger."""

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn

    def log(self, entry: ConversationLogEntry) -> None:
        try:
            created_at = datetime.now(timezone.utc).isoformat()
            with postgres_connect(self._dsn) as conn:
                conn.execute(
                    """
                    INSERT INTO conversations
                        (created_at, ip, model, turn_count, user_message, assistant_response, response_ms, user_name, session_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        created_at,
                        entry.ip,
                        entry.model,
                        entry.turn_count,
                        entry.user_message,
                        entry.assistant_response,
                        entry.response_ms,
                        entry.user_name,
                        entry.session_id,
                    ),
                )
        except Exception:
            log_service.logger.error(
                "Failed to log conversation to Postgres",
                extra={
                    "event": "postgres_log_write_failure",
                    "component": "chat_runtime.PostgresConversationLogger.log",
                },
                exc_info=True,
            )


class OllamaTitleGenerator:
    """Ollama-backed TitleGenerator using the injectable LLM client (no direct HTTP here)."""

    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm

    def generate_title(
        self,
        *,
        model: str,
        user_text: str,
        assistant_text: str,
    ) -> str | None:
        prompt = (
            "Write ONE chat sidebar title for this exchange. "
            "If the title is in English, keep it to 26 characters or fewer. "
            "If the title is in Chinese, keep it to 15 characters or fewer. "
            "Output only the title text, no quotes, no labels, no decorative punctuation.\n\n"
            f"User: {user_text[:4000]}\n\nAssistant: {assistant_text[:4000]}"
        )
        text = self._llm.generate_completion(model, prompt)
        one_line = " ".join(text.splitlines()).strip()
        if not one_line:
            return None
        return one_line
