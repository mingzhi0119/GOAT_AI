"""Create hosted Postgres runtime metadata baseline for Phase 16D."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260413_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "schema_migrations",
        sa.Column("id", sa.Text(), primary_key=True, nullable=False),
        sa.Column("applied_at", sa.Text(), nullable=False),
        sa.Column("checksum", sa.Text(), nullable=False),
    )

    op.create_table(
        "conversations",
        sa.Column(
            "id",
            sa.BigInteger(),
            sa.Identity(always=False),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("ip", sa.Text(), nullable=False),
        sa.Column("model", sa.Text(), nullable=False),
        sa.Column("turn_count", sa.Integer(), nullable=False),
        sa.Column("user_message", sa.Text(), nullable=False),
        sa.Column("assistant_response", sa.Text(), nullable=False),
        sa.Column("response_ms", sa.Integer(), nullable=True),
        sa.Column(
            "user_name",
            sa.Text(),
            nullable=False,
            server_default=sa.text("''"),
        ),
        sa.Column("session_id", sa.Text(), nullable=True),
    )

    op.create_table(
        "sessions",
        sa.Column("id", sa.Text(), primary_key=True, nullable=False),
        sa.Column("title", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column("model", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.Column(
            "messages", sa.Text(), nullable=False, server_default=sa.text("'[]'")
        ),
        sa.Column(
            "schema_version",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
        ),
        sa.Column("owner_id", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column(
            "tenant_id",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'tenant:default'"),
        ),
        sa.Column(
            "principal_id", sa.Text(), nullable=False, server_default=sa.text("''")
        ),
    )
    op.create_index("idx_sessions_tenant_id", "sessions", ["tenant_id"])

    op.create_table(
        "session_messages",
        sa.Column("session_id", sa.Text(), nullable=False),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("image_attachment_ids", sa.Text(), nullable=True),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("artifacts_json", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("session_id", "seq"),
    )
    op.create_index("idx_session_messages_session", "session_messages", ["session_id"])

    op.create_table(
        "idempotency_keys",
        sa.Column("key", sa.Text(), nullable=False),
        sa.Column("route", sa.Text(), nullable=False),
        sa.Column("scope", sa.Text(), nullable=False),
        sa.Column("request_hash", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("response_status", sa.Integer(), nullable=True),
        sa.Column("response_content_type", sa.Text(), nullable=True),
        sa.Column("response_body", sa.Text(), nullable=True),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("key", "route", "scope"),
    )
    op.create_index(
        "idx_idempotency_keys_expires_at", "idempotency_keys", ["expires_at"]
    )

    op.create_table(
        "chat_artifacts",
        sa.Column("id", sa.Text(), primary_key=True, nullable=False),
        sa.Column(
            "session_id", sa.Text(), nullable=False, server_default=sa.text("''")
        ),
        sa.Column("owner_id", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column("filename", sa.Text(), nullable=False),
        sa.Column("mime_type", sa.Text(), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column(
            "source_message_index",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column(
            "tenant_id",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'tenant:default'"),
        ),
        sa.Column(
            "principal_id", sa.Text(), nullable=False, server_default=sa.text("''")
        ),
        sa.Column(
            "storage_key", sa.Text(), nullable=False, server_default=sa.text("''")
        ),
    )
    op.create_index("idx_chat_artifacts_session_id", "chat_artifacts", ["session_id"])
    op.create_index("idx_chat_artifacts_owner_id", "chat_artifacts", ["owner_id"])
    op.create_index("idx_chat_artifacts_tenant_id", "chat_artifacts", ["tenant_id"])

    op.create_table(
        "knowledge_documents",
        sa.Column("id", sa.Text(), primary_key=True, nullable=False),
        sa.Column("source_type", sa.Text(), nullable=False),
        sa.Column("original_filename", sa.Text(), nullable=False),
        sa.Column("mime_type", sa.Text(), nullable=False),
        sa.Column("sha256", sa.Text(), nullable=False),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.Column("deleted_at", sa.Text(), nullable=True),
        sa.Column("owner_id", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column(
            "tenant_id",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'tenant:default'"),
        ),
        sa.Column(
            "principal_id", sa.Text(), nullable=False, server_default=sa.text("''")
        ),
        sa.Column(
            "storage_key", sa.Text(), nullable=False, server_default=sa.text("''")
        ),
    )
    op.create_index("idx_knowledge_documents_status", "knowledge_documents", ["status"])
    op.create_index(
        "idx_knowledge_documents_created_at", "knowledge_documents", ["created_at"]
    )
    op.create_index(
        "idx_knowledge_documents_tenant_id", "knowledge_documents", ["tenant_id"]
    )

    op.create_table(
        "knowledge_ingestions",
        sa.Column("id", sa.Text(), primary_key=True, nullable=False),
        sa.Column("document_id", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("parser_profile", sa.Text(), nullable=False),
        sa.Column("chunking_profile", sa.Text(), nullable=False),
        sa.Column("embedding_profile", sa.Text(), nullable=False),
        sa.Column("vector_backend", sa.Text(), nullable=False),
        sa.Column("started_at", sa.Text(), nullable=True),
        sa.Column("completed_at", sa.Text(), nullable=True),
        sa.Column("error_code", sa.Text(), nullable=True),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column(
            "chunk_count", sa.Integer(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["knowledge_documents.id"]),
    )
    op.create_index(
        "idx_knowledge_ingestions_document_id",
        "knowledge_ingestions",
        ["document_id"],
    )
    op.create_index(
        "idx_knowledge_ingestions_status", "knowledge_ingestions", ["status"]
    )
    op.create_index(
        "idx_knowledge_ingestions_created_at",
        "knowledge_ingestions",
        ["created_at"],
    )

    op.create_table(
        "knowledge_chunks",
        sa.Column("id", sa.Text(), primary_key=True, nullable=False),
        sa.Column("ingestion_id", sa.Text(), nullable=False),
        sa.Column("document_id", sa.Text(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("text_content", sa.Text(), nullable=False),
        sa.Column("text_hash", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=True),
        sa.Column("char_start", sa.Integer(), nullable=True),
        sa.Column("char_end", sa.Integer(), nullable=True),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("section_label", sa.Text(), nullable=True),
        sa.Column("vector_ref", sa.Text(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["ingestion_id"], ["knowledge_ingestions.id"]),
        sa.ForeignKeyConstraint(["document_id"], ["knowledge_documents.id"]),
    )
    op.create_index(
        "idx_knowledge_chunks_ingestion_chunk",
        "knowledge_chunks",
        ["ingestion_id", "chunk_index"],
        unique=True,
    )
    op.create_index(
        "idx_knowledge_chunks_document_id", "knowledge_chunks", ["document_id"]
    )
    op.create_index(
        "idx_knowledge_chunks_vector_ref", "knowledge_chunks", ["vector_ref"]
    )

    op.create_table(
        "media_uploads",
        sa.Column("id", sa.Text(), primary_key=True, nullable=False),
        sa.Column("owner_id", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column(
            "tenant_id",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'tenant:default'"),
        ),
        sa.Column(
            "principal_id", sa.Text(), nullable=False, server_default=sa.text("''")
        ),
        sa.Column("filename", sa.Text(), nullable=False),
        sa.Column("mime_type", sa.Text(), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column("width_px", sa.Integer(), nullable=True),
        sa.Column("height_px", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column(
            "storage_key", sa.Text(), nullable=False, server_default=sa.text("''")
        ),
    )
    op.create_index("idx_media_uploads_tenant_id", "media_uploads", ["tenant_id"])

    op.create_table(
        "workbench_tasks",
        sa.Column("id", sa.Text(), primary_key=True, nullable=False),
        sa.Column("task_kind", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("session_id", sa.Text(), nullable=True),
        sa.Column("project_id", sa.Text(), nullable=True),
        sa.Column(
            "knowledge_document_ids",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'[]'"),
        ),
        sa.Column(
            "connector_ids", sa.Text(), nullable=False, server_default=sa.text("'[]'")
        ),
        sa.Column(
            "source_ids", sa.Text(), nullable=False, server_default=sa.text("'[]'")
        ),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column("result_text", sa.Text(), nullable=True),
        sa.Column("result_citations_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.Column(
            "auth_scopes_json",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'[]'"),
        ),
        sa.Column(
            "credential_id", sa.Text(), nullable=False, server_default=sa.text("''")
        ),
        sa.Column("auth_mode", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column("owner_id", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column(
            "tenant_id",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'tenant:default'"),
        ),
        sa.Column(
            "principal_id", sa.Text(), nullable=False, server_default=sa.text("''")
        ),
        sa.CheckConstraint(
            "task_kind IN ('plan', 'browse', 'deep_research', 'canvas')",
            name="ck_workbench_tasks_task_kind",
        ),
        sa.CheckConstraint(
            "status IN ('queued', 'running', 'completed', 'failed', 'cancelled')",
            name="ck_workbench_tasks_status",
        ),
    )
    op.create_index(
        "idx_workbench_tasks_tenant_created",
        "workbench_tasks",
        ["tenant_id", "created_at"],
    )
    op.create_index(
        "idx_workbench_tasks_owner_created",
        "workbench_tasks",
        ["owner_id", "created_at"],
    )

    op.create_table(
        "workbench_task_events",
        sa.Column(
            "id",
            sa.BigInteger(),
            sa.Identity(always=False),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("task_id", sa.Text(), nullable=False),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["task_id"], ["workbench_tasks.id"], ondelete="CASCADE"
        ),
    )
    op.create_index(
        "idx_workbench_task_events_task_seq",
        "workbench_task_events",
        ["task_id", "seq"],
        unique=True,
    )
    op.create_index(
        "idx_workbench_task_events_task_created",
        "workbench_task_events",
        ["task_id", "created_at", "seq"],
    )

    op.create_table(
        "code_sandbox_executions",
        sa.Column("id", sa.Text(), primary_key=True, nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("runtime_preset", sa.Text(), nullable=False),
        sa.Column("network_policy", sa.Text(), nullable=False),
        sa.Column("code", sa.Text(), nullable=True),
        sa.Column("command", sa.Text(), nullable=True),
        sa.Column("stdin_text", sa.Text(), nullable=True),
        sa.Column(
            "inline_files_json",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'[]'"),
        ),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.Column("started_at", sa.Text(), nullable=True),
        sa.Column("finished_at", sa.Text(), nullable=True),
        sa.Column("exit_code", sa.Integer(), nullable=True),
        sa.Column("stdout", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column("stderr", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column(
            "timed_out", sa.Integer(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column("output_files_json", sa.Text(), nullable=True),
        sa.Column(
            "provider_name", sa.Text(), nullable=False, server_default=sa.text("''")
        ),
        sa.Column("owner_id", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column(
            "tenant_id",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'tenant:default'"),
        ),
        sa.Column(
            "principal_id", sa.Text(), nullable=False, server_default=sa.text("''")
        ),
        sa.Column(
            "auth_scopes_json",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'[]'"),
        ),
        sa.Column(
            "credential_id", sa.Text(), nullable=False, server_default=sa.text("''")
        ),
        sa.Column("auth_mode", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column(
            "execution_mode",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'sync'"),
        ),
        sa.Column("queued_at", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column(
            "timeout_sec", sa.Integer(), nullable=False, server_default=sa.text("8")
        ),
        sa.Column(
            "last_log_seq", sa.Integer(), nullable=False, server_default=sa.text("0")
        ),
    )
    op.create_index(
        "idx_code_sandbox_executions_updated_at",
        "code_sandbox_executions",
        ["updated_at"],
    )

    op.create_table(
        "code_sandbox_execution_events",
        sa.Column("execution_id", sa.Text(), nullable=False),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("execution_id", "seq"),
        sa.ForeignKeyConstraint(
            ["execution_id"],
            ["code_sandbox_executions.id"],
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "idx_code_sandbox_execution_events_created_at",
        "code_sandbox_execution_events",
        ["execution_id", "created_at"],
    )

    op.create_table(
        "code_sandbox_execution_logs",
        sa.Column("execution_id", sa.Text(), nullable=False),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("stream_name", sa.Text(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("chunk_text", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("execution_id", "seq"),
        sa.ForeignKeyConstraint(
            ["execution_id"],
            ["code_sandbox_executions.id"],
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "idx_code_sandbox_execution_logs_created_at",
        "code_sandbox_execution_logs",
        ["execution_id", "created_at"],
    )

    op.create_table(
        "workbench_workspace_outputs",
        sa.Column("id", sa.Text(), primary_key=True, nullable=False),
        sa.Column("task_id", sa.Text(), nullable=False),
        sa.Column("output_kind", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("content_format", sa.Text(), nullable=False),
        sa.Column("content_text", sa.Text(), nullable=False),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.Column("owner_id", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column(
            "tenant_id",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'tenant:default'"),
        ),
        sa.Column(
            "principal_id", sa.Text(), nullable=False, server_default=sa.text("''")
        ),
        sa.ForeignKeyConstraint(
            ["task_id"], ["workbench_tasks.id"], ondelete="CASCADE"
        ),
        sa.CheckConstraint(
            "output_kind IN ('canvas_document')",
            name="ck_workbench_workspace_outputs_output_kind",
        ),
        sa.CheckConstraint(
            "content_format IN ('markdown')",
            name="ck_workbench_workspace_outputs_content_format",
        ),
    )
    op.create_index(
        "idx_workbench_workspace_outputs_task_created",
        "workbench_workspace_outputs",
        ["task_id", "created_at", "id"],
    )
    op.create_index(
        "idx_workbench_workspace_outputs_tenant_created",
        "workbench_workspace_outputs",
        ["tenant_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "idx_workbench_workspace_outputs_tenant_created",
        table_name="workbench_workspace_outputs",
    )
    op.drop_index(
        "idx_workbench_workspace_outputs_task_created",
        table_name="workbench_workspace_outputs",
    )
    op.drop_table("workbench_workspace_outputs")

    op.drop_index(
        "idx_code_sandbox_execution_logs_created_at",
        table_name="code_sandbox_execution_logs",
    )
    op.drop_table("code_sandbox_execution_logs")
    op.drop_index(
        "idx_code_sandbox_execution_events_created_at",
        table_name="code_sandbox_execution_events",
    )
    op.drop_table("code_sandbox_execution_events")
    op.drop_index(
        "idx_code_sandbox_executions_updated_at",
        table_name="code_sandbox_executions",
    )
    op.drop_table("code_sandbox_executions")

    op.drop_index(
        "idx_workbench_task_events_task_created",
        table_name="workbench_task_events",
    )
    op.drop_index(
        "idx_workbench_task_events_task_seq",
        table_name="workbench_task_events",
    )
    op.drop_table("workbench_task_events")
    op.drop_index("idx_workbench_tasks_owner_created", table_name="workbench_tasks")
    op.drop_index("idx_workbench_tasks_tenant_created", table_name="workbench_tasks")
    op.drop_table("workbench_tasks")

    op.drop_index("idx_media_uploads_tenant_id", table_name="media_uploads")
    op.drop_table("media_uploads")

    op.drop_index("idx_knowledge_chunks_vector_ref", table_name="knowledge_chunks")
    op.drop_index("idx_knowledge_chunks_document_id", table_name="knowledge_chunks")
    op.drop_index(
        "idx_knowledge_chunks_ingestion_chunk",
        table_name="knowledge_chunks",
    )
    op.drop_table("knowledge_chunks")
    op.drop_index(
        "idx_knowledge_ingestions_created_at",
        table_name="knowledge_ingestions",
    )
    op.drop_index("idx_knowledge_ingestions_status", table_name="knowledge_ingestions")
    op.drop_index(
        "idx_knowledge_ingestions_document_id",
        table_name="knowledge_ingestions",
    )
    op.drop_table("knowledge_ingestions")
    op.drop_index(
        "idx_knowledge_documents_tenant_id",
        table_name="knowledge_documents",
    )
    op.drop_index(
        "idx_knowledge_documents_created_at",
        table_name="knowledge_documents",
    )
    op.drop_index("idx_knowledge_documents_status", table_name="knowledge_documents")
    op.drop_table("knowledge_documents")

    op.drop_index("idx_chat_artifacts_tenant_id", table_name="chat_artifacts")
    op.drop_index("idx_chat_artifacts_owner_id", table_name="chat_artifacts")
    op.drop_index("idx_chat_artifacts_session_id", table_name="chat_artifacts")
    op.drop_table("chat_artifacts")

    op.drop_index(
        "idx_idempotency_keys_expires_at",
        table_name="idempotency_keys",
    )
    op.drop_table("idempotency_keys")

    op.drop_index("idx_session_messages_session", table_name="session_messages")
    op.drop_table("session_messages")
    op.drop_index("idx_sessions_tenant_id", table_name="sessions")
    op.drop_table("sessions")

    op.drop_table("conversations")
    op.drop_table("schema_migrations")
