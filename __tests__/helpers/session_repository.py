from __future__ import annotations

from backend.services.artifact_service import PersistedArtifactRecord
from backend.services.chat_runtime import (
    SessionDetailRecord,
    SessionSummaryRecord,
    SessionUpsertPayload,
)
from backend.services.session_message_codec import decode_session_payload


class InMemorySessionRepository:
    """Minimal dict-backed repository for session-storage tests."""

    def __init__(self) -> None:
        self._rows: dict[str, dict[str, object]] = {}
        self._artifacts: dict[str, PersistedArtifactRecord] = {}

    def list_sessions(
        self,
        owner_filter: str | None = None,
        *,
        tenant_filter: str | None = None,
    ) -> list[SessionSummaryRecord]:
        out: list[SessionSummaryRecord] = []
        for sid, row in sorted(
            self._rows.items(), key=lambda kv: str(kv[1].get("updated_at", ""))
        ):
            row_owner = str(row.get("owner_id", ""))
            if owner_filter is not None and row_owner != owner_filter:
                continue
            row_tenant = str(row.get("tenant_id", "tenant:default"))
            if tenant_filter is not None and row_tenant != tenant_filter:
                continue
            out.append(
                SessionSummaryRecord(
                    id=sid,
                    title=str(row["title"]),
                    model=str(row["model"]),
                    schema_version=int(row.get("schema_version", 1)),
                    created_at=str(row["created_at"]),
                    updated_at=str(row["updated_at"]),
                    owner_id=row_owner,
                    tenant_id=row_tenant,
                    principal_id=str(row.get("principal_id", "")),
                )
            )
        return out

    def get_session(self, session_id: str) -> SessionDetailRecord | None:
        row = self._rows.get(session_id)
        if row is None:
            return None
        raw_messages = row.get("messages", [])
        decoded = decode_session_payload(
            raw_messages if isinstance(raw_messages, (list, dict)) else []
        )
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
        )

    def upsert_session(self, payload: SessionUpsertPayload) -> None:
        self._rows[payload.session_id] = {
            "id": payload.session_id,
            "title": payload.title,
            "model": payload.model,
            "schema_version": payload.schema_version,
            "created_at": payload.created_at,
            "updated_at": payload.updated_at,
            "messages": payload.payload,
            "owner_id": payload.owner_id,
            "tenant_id": payload.tenant_id,
            "principal_id": payload.principal_id,
        }

    def delete_session(self, session_id: str) -> None:
        self._rows.pop(session_id, None)

    def rename_session(self, session_id: str, title: str) -> None:
        row = self._rows.get(session_id)
        if row is None:
            return
        row["title"] = title

    def delete_all_sessions(
        self,
        owner_filter: str | None = None,
        *,
        tenant_filter: str | None = None,
    ) -> None:
        if owner_filter is None and tenant_filter is None:
            self._rows.clear()
            return
        for sid in [
            k
            for k, row in self._rows.items()
            if (owner_filter is None or str(row.get("owner_id", "")) == owner_filter)
            and (
                tenant_filter is None
                or str(row.get("tenant_id", "tenant:default")) == tenant_filter
            )
        ]:
            del self._rows[sid]

    def create_chat_artifact(self, record: PersistedArtifactRecord) -> None:
        self._artifacts[record.id] = record

    def get_chat_artifact(self, artifact_id: str) -> PersistedArtifactRecord | None:
        return self._artifacts.get(artifact_id)
