"""Canonical Phase 16D runtime-metadata inventory and deterministic table order."""

from __future__ import annotations


RUNTIME_METADATA_TABLES: tuple[str, ...] = (
    "conversations",
    "sessions",
    "session_messages",
    "idempotency_keys",
    "chat_artifacts",
    "knowledge_documents",
    "knowledge_ingestions",
    "knowledge_chunks",
    "media_uploads",
    "workbench_tasks",
    "workbench_task_events",
    "workbench_workspace_outputs",
    "code_sandbox_executions",
    "code_sandbox_execution_events",
    "code_sandbox_execution_logs",
    "schema_migrations",
)

_RUNTIME_METADATA_ORDER_BY: dict[str, str] = {
    "conversations": "id ASC",
    "sessions": "id ASC",
    "session_messages": "session_id ASC, seq ASC",
    "idempotency_keys": "key ASC, route ASC, scope ASC",
    "chat_artifacts": "id ASC",
    "knowledge_documents": "id ASC",
    "knowledge_ingestions": "id ASC",
    "knowledge_chunks": "document_id ASC, chunk_index ASC, id ASC",
    "media_uploads": "id ASC",
    "workbench_tasks": "created_at ASC, id ASC",
    "workbench_task_events": "task_id ASC, seq ASC",
    "workbench_workspace_outputs": "task_id ASC, created_at ASC, id ASC",
    "code_sandbox_executions": "queued_at ASC, created_at ASC, id ASC",
    "code_sandbox_execution_events": "execution_id ASC, seq ASC",
    "code_sandbox_execution_logs": "execution_id ASC, seq ASC",
    "schema_migrations": "id ASC",
}


def runtime_metadata_order_by(table_name: str) -> str:
    """Return the deterministic row ordering used for snapshot export."""
    try:
        return _RUNTIME_METADATA_ORDER_BY[table_name]
    except KeyError as exc:
        raise KeyError(f"Unknown runtime metadata table: {table_name}") from exc
