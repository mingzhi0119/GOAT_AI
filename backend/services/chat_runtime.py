"""Typed runtime interfaces and adapters for chat/session infrastructure."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from backend.services import log_service
from backend.services.session_message_codec import decode_session_payload
from goat_ai.ollama_client import LLMClient


@dataclass(frozen=True)
class SessionSummaryRecord:
    """Typed session summary returned by the history repository."""

    id: str
    title: str
    model: str
    schema_version: int
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class SessionDetailRecord(SessionSummaryRecord):
    """Typed session detail returned by the history repository."""

    messages: list[dict[str, str]]
    chart_spec: dict[str, object] | None = None
    file_context_prompt: str | None = None
    knowledge_documents: list[dict[str, str]] | None = None
    chart_data_source: str | None = None


@dataclass(frozen=True)
class SessionUpsertPayload:
    """Payload required to persist a chat session snapshot."""

    session_id: str
    title: str
    model: str
    schema_version: int
    payload: dict[str, object]
    created_at: str
    updated_at: str


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

    def list_sessions(self) -> list[SessionSummaryRecord]: ...

    def get_session(self, session_id: str) -> SessionDetailRecord | None: ...

    def upsert_session(self, payload: SessionUpsertPayload) -> None: ...

    def delete_session(self, session_id: str) -> None: ...

    def delete_all_sessions(self) -> None: ...


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

    def list_sessions(self) -> list[SessionSummaryRecord]:
        rows = log_service.list_sessions(db_path=self._db_path)
        return [
            SessionSummaryRecord(
                id=str(row["id"]),
                title=str(row["title"]),
                model=str(row["model"]),
                schema_version=int(row.get("schema_version", 1)),
                created_at=str(row["created_at"]),
                updated_at=str(row["updated_at"]),
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
            messages=decoded.messages,
            chart_spec=decoded.chart_spec,
            file_context_prompt=decoded.file_context_prompt,
            knowledge_documents=decoded.knowledge_documents,
            chart_data_source=decoded.chart_data_source,
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
        )

    def delete_session(self, session_id: str) -> None:
        log_service.delete_session(db_path=self._db_path, session_id=session_id)

    def delete_all_sessions(self) -> None:
        log_service.delete_all_sessions(db_path=self._db_path)


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
            "Write ONE short line (maximum 12 words) summarizing this exchange for a chat sidebar title. "
            "Output only the title text, no quotes, no role labels.\n\n"
            f"User: {user_text[:4000]}\n\nAssistant: {assistant_text[:4000]}"
        )
        text = self._llm.generate_completion(model, prompt)
        one_line = " ".join(text.splitlines()).strip()
        if not one_line:
            return None
        return one_line[:120] if len(one_line) > 120 else one_line
