from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import threading
import unittest
from unittest.mock import patch

from __tests__.helpers.postgres_runtime import postgres_runtime_container
from backend.services.artifact_service import PersistedArtifactRecord
from backend.services.chat_runtime import (
    ConversationLogEntry,
    PostgresConversationLogger,
    PostgresSessionRepository,
    SessionUpsertPayload,
)
from backend.services.code_sandbox_runtime import (
    CodeSandboxExecutionCreatePayload,
    PostgresCodeSandboxExecutionRepository,
)
from backend.services.idempotency_service import PostgresIdempotencyStore
from backend.services.knowledge_repository import (
    KnowledgeChunkRow,
    KnowledgeDocumentRecord,
    KnowledgeIngestionRecord,
    PostgresKnowledgeRepository,
)
from backend.services.media_service import MediaUploadRecord, PostgresMediaRepository
from backend.services.postgres_runtime_support import (
    postgres_connect as runtime_postgres_connect,
    run_postgres_runtime_migrations,
)
from backend.services.workbench_runtime import (
    PostgresWorkbenchTaskRepository,
    WorkbenchTaskCreatePayload,
    WorkbenchWorkspaceOutputCreatePayload,
)
from goat_ai.shared.clocks import FakeClock


class _BarrierPostgresConnection:
    def __init__(self, dsn: str, barrier: threading.Barrier) -> None:
        self._conn = runtime_postgres_connect(dsn)
        self._barrier = barrier

    def __enter__(self) -> _BarrierPostgresConnection:
        self._conn.__enter__()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self._conn.__exit__(exc_type, exc, tb)

    def transaction(self):
        return self._conn.transaction()

    def execute(self, query, params=None):
        if "INSERT INTO idempotency_keys" in str(query):
            self._barrier.wait(timeout=5)
        if params is None:
            return self._conn.execute(query)
        return self._conn.execute(query, params)

    def __getattr__(self, name: str):
        return getattr(self._conn, name)


class PostgresRuntimeContractsTests(unittest.TestCase):
    def test_chat_runtime_contract_round_trip(self) -> None:
        with postgres_runtime_container() as dsn:
            run_postgres_runtime_migrations(dsn)
            sessions = PostgresSessionRepository(dsn)
            conversations = PostgresConversationLogger(dsn)

            sessions.upsert_session(
                SessionUpsertPayload(
                    session_id="session-1",
                    title="Session",
                    model="llama3",
                    schema_version=4,
                    payload={
                        "version": 4,
                        "messages": [
                            {"role": "user", "content": "hello"},
                            {
                                "role": "assistant",
                                "content": "world",
                                "artifacts": [{"artifact_id": "art-1"}],
                            },
                        ],
                    },
                    created_at="2026-04-13T10:00:00Z",
                    updated_at="2026-04-13T10:00:01Z",
                    owner_id="owner-1",
                    tenant_id="tenant-1",
                    principal_id="principal-1",
                )
            )
            conversations.log(
                ConversationLogEntry(
                    ip="127.0.0.1",
                    model="llama3",
                    turn_count=1,
                    user_message="hello",
                    assistant_response="world",
                    response_ms=15,
                    user_name="user",
                    session_id="session-1",
                )
            )
            sessions.create_chat_artifact(
                PersistedArtifactRecord(
                    id="art-1",
                    session_id="session-1",
                    owner_id="owner-1",
                    tenant_id="tenant-1",
                    principal_id="principal-1",
                    filename="answer.md",
                    mime_type="text/markdown",
                    byte_size=12,
                    storage_path="/tmp/answer.md",
                    storage_key="artifacts/answer.md",
                    source_message_index=1,
                    created_at="2026-04-13T10:00:01Z",
                )
            )

            listed = sessions.list_sessions(
                owner_filter="owner-1", tenant_filter="tenant-1"
            )
            self.assertEqual(["session-1"], [row.id for row in listed])
            detail = sessions.get_session("session-1")
            assert detail is not None
            self.assertEqual(
                ["hello", "world"], [msg["content"] for msg in detail.messages]
            )
            artifact = sessions.get_chat_artifact("art-1")
            assert artifact is not None
            self.assertEqual("artifacts/answer.md", artifact.storage_key)

    def test_idempotency_store_claim_replay_and_release(self) -> None:
        with postgres_runtime_container() as dsn:
            run_postgres_runtime_migrations(dsn)
            store = PostgresIdempotencyStore(
                dsn=dsn,
                ttl_sec=300,
                clock=FakeClock("2026-04-13T10:00:00+00:00"),
            )

            claimed = store.claim(
                key="idem-1",
                route="/api/chat",
                scope="tenant:default",
                request_hash="hash-1",
            )
            self.assertEqual("claimed", claimed.state)
            in_progress = store.claim(
                key="idem-1",
                route="/api/chat",
                scope="tenant:default",
                request_hash="hash-1",
            )
            self.assertEqual("in_progress", in_progress.state)
            store.store_completed(
                key="idem-1",
                route="/api/chat",
                scope="tenant:default",
                request_hash="hash-1",
                status_code=200,
                content_type="application/json",
                body='{"ok":true}',
            )
            replay = store.claim(
                key="idem-1",
                route="/api/chat",
                scope="tenant:default",
                request_hash="hash-1",
            )
            self.assertEqual("replay", replay.state)
            self.assertEqual(200, replay.completed.status_code)
            store.release_pending(
                key="idem-2",
                route="/api/chat",
                scope="tenant:default",
                request_hash="hash-2",
            )

    def test_idempotency_store_first_claim_is_concurrency_safe(self) -> None:
        with postgres_runtime_container() as dsn:
            run_postgres_runtime_migrations(dsn)
            barrier = threading.Barrier(2)
            stores = [
                PostgresIdempotencyStore(
                    dsn=dsn,
                    ttl_sec=300,
                    clock=FakeClock("2026-04-13T10:00:00+00:00"),
                ),
                PostgresIdempotencyStore(
                    dsn=dsn,
                    ttl_sec=300,
                    clock=FakeClock("2026-04-13T10:00:00+00:00"),
                ),
            ]

            def connect_with_barrier(connect_dsn: str) -> _BarrierPostgresConnection:
                return _BarrierPostgresConnection(connect_dsn, barrier)

            def claim_once(store: PostgresIdempotencyStore):
                return store.claim(
                    key="idem-race",
                    route="/api/chat",
                    scope="tenant:default",
                    request_hash="hash-race",
                )

            with patch(
                "backend.services.idempotency_service.postgres_connect",
                side_effect=connect_with_barrier,
            ):
                with ThreadPoolExecutor(max_workers=2) as executor:
                    futures = [executor.submit(claim_once, store) for store in stores]
                    outcomes = [future.result(timeout=10) for future in futures]

            self.assertCountEqual(
                [outcome.state for outcome in outcomes],
                ["claimed", "in_progress"],
            )

    def test_knowledge_and_media_contract_round_trip(self) -> None:
        with postgres_runtime_container() as dsn:
            run_postgres_runtime_migrations(dsn)
            knowledge = PostgresKnowledgeRepository(dsn)
            media = PostgresMediaRepository(dsn)

            knowledge.create_document(
                KnowledgeDocumentRecord(
                    id="doc-1",
                    source_type="upload",
                    original_filename="notes.md",
                    mime_type="text/markdown",
                    sha256="abc",
                    storage_path="/tmp/notes.md",
                    storage_key="knowledge/doc-1",
                    byte_size=8,
                    status="ready",
                    created_at="2026-04-13T10:00:00Z",
                    updated_at="2026-04-13T10:00:00Z",
                    deleted_at=None,
                    owner_id="owner-1",
                    tenant_id="tenant-1",
                    principal_id="principal-1",
                )
            )
            knowledge.create_ingestion(
                KnowledgeIngestionRecord(
                    id="ing-1",
                    document_id="doc-1",
                    status="running",
                    parser_profile="default",
                    chunking_profile="default",
                    embedding_profile="default",
                    vector_backend="none",
                    started_at=None,
                    completed_at=None,
                    error_code=None,
                    error_detail=None,
                    chunk_count=0,
                    created_at="2026-04-13T10:00:01Z",
                    updated_at="2026-04-13T10:00:01Z",
                )
            )
            knowledge.replace_chunks(
                ingestion_id="ing-1",
                document_id="doc-1",
                chunks=[
                    KnowledgeChunkRow(
                        id="chunk-1",
                        ingestion_id="ing-1",
                        document_id="doc-1",
                        chunk_index=0,
                        text_content="alpha",
                        text_hash="hash",
                        token_count=1,
                        char_start=0,
                        char_end=5,
                        vector_ref="vec-1",
                        created_at="2026-04-13T10:00:02Z",
                    )
                ],
            )
            media.create_media_upload(
                MediaUploadRecord(
                    id="att-1",
                    owner_id="owner-1",
                    tenant_id="tenant-1",
                    principal_id="principal-1",
                    filename="image.png",
                    mime_type="image/png",
                    byte_size=10,
                    storage_path="/tmp/image.png",
                    storage_key="uploads/media/att-1",
                    width_px=1,
                    height_px=1,
                    created_at="2026-04-13T10:00:02Z",
                )
            )

            self.assertEqual("doc-1", knowledge.get_document("doc-1").id)
            self.assertEqual("ing-1", knowledge.get_ingestion("ing-1").id)
            self.assertEqual(
                ["chunk-1"],
                [row.id for row in knowledge.get_chunks_for_documents(["doc-1"])],
            )
            self.assertEqual("att-1", media.get_media_upload("att-1").id)

    def test_workbench_runtime_contract_round_trip(self) -> None:
        with postgres_runtime_container() as dsn:
            run_postgres_runtime_migrations(dsn)
            repository = PostgresWorkbenchTaskRepository(dsn)

            repository.create_task(
                WorkbenchTaskCreatePayload(
                    task_id="wb-1",
                    task_kind="plan",
                    prompt="Draft a plan",
                    session_id="session-1",
                    project_id="project-1",
                    knowledge_document_ids=[],
                    connector_ids=[],
                    source_ids=[],
                    created_at="2026-04-13T10:00:00Z",
                    updated_at="2026-04-13T10:00:00Z",
                    auth_scopes=["workbench:write"],
                    credential_id="cred-1",
                    auth_mode="api_key",
                )
            )
            claimed = repository.claim_task_for_execution(
                "wb-1",
                updated_at="2026-04-13T10:00:01Z",
            )
            assert claimed is not None
            repository.create_workspace_output(
                WorkbenchWorkspaceOutputCreatePayload(
                    output_id="out-1",
                    task_id="wb-1",
                    output_kind="canvas_document",
                    title="Draft",
                    content_format="markdown",
                    content_text="# Draft",
                    metadata={"editable": True},
                    created_at="2026-04-13T10:00:02Z",
                    updated_at="2026-04-13T10:00:02Z",
                )
            )
            repository.mark_task_completed(
                "wb-1",
                updated_at="2026-04-13T10:00:03Z",
                result_text="# Done",
                result_citations=[{"document_id": "doc-1"}],
                workspace_output_count=1,
            )

            stored = repository.get_task("wb-1")
            assert stored is not None
            self.assertEqual("completed", stored.status)
            self.assertEqual(
                ["out-1"], [row.id for row in repository.list_workspace_outputs("wb-1")]
            )
            self.assertEqual(
                [
                    "task.queued",
                    "task.started",
                    "workspace_output.created",
                    "task.completed",
                ],
                [event.event_type for event in repository.list_task_events("wb-1")],
            )

    def test_code_sandbox_runtime_contract_round_trip(self) -> None:
        with postgres_runtime_container() as dsn:
            run_postgres_runtime_migrations(dsn)
            repository = PostgresCodeSandboxExecutionRepository(dsn)

            repository.create_execution(
                CodeSandboxExecutionCreatePayload(
                    execution_id="cs-1",
                    execution_mode="async",
                    runtime_preset="shell",
                    network_policy="disabled",
                    timeout_sec=8,
                    code="echo hi",
                    command=None,
                    stdin=None,
                    inline_files=[],
                    created_at="2026-04-13T10:00:00Z",
                    queued_at="2026-04-13T10:00:00Z",
                    updated_at="2026-04-13T10:00:00Z",
                    provider_name="docker",
                    owner_id="owner-1",
                    tenant_id="tenant-1",
                    principal_id="principal-1",
                    auth_scopes=["sandbox:execute"],
                    credential_id="cred-1",
                    auth_mode="api_key",
                )
            )
            repository.mark_execution_started(
                "cs-1",
                updated_at="2026-04-13T10:00:01Z",
                provider_name="docker",
            )
            repository.append_log_chunk(
                "cs-1",
                created_at="2026-04-13T10:00:02Z",
                stream_name="stdout",
                chunk_text="hello\n",
            )
            repository.mark_execution_completed(
                "cs-1",
                updated_at="2026-04-13T10:00:03Z",
                finished_at="2026-04-13T10:00:03Z",
                exit_code=0,
                stdout="hello\n",
                stderr="",
                timed_out=False,
                error_detail=None,
                output_files=[{"path": "report.txt"}],
            )

            record = repository.get_execution("cs-1")
            assert record is not None
            self.assertEqual("completed", record.status)
            self.assertEqual(1, record.last_log_seq)
            self.assertEqual(
                ["hello\n"],
                [row.chunk_text for row in repository.list_log_chunks("cs-1")],
            )
            self.assertEqual(
                [
                    "execution.queued",
                    "execution.started",
                    "execution.log.stdout",
                    "execution.completed",
                ],
                [
                    event.event_type
                    for event in repository.list_execution_events("cs-1")
                ],
            )


if __name__ == "__main__":
    unittest.main()
