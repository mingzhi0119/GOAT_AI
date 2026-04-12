from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from backend.services.db_migrations import apply_migrations
from backend.services.code_sandbox_runtime import (
    CodeSandboxExecutionCreatePayload,
    SQLiteCodeSandboxExecutionRepository,
)


class CodeSandboxRuntimeTests(unittest.TestCase):
    def test_repository_persists_execution_lifecycle_and_events(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            db_path = Path(tmp) / "sandbox.db"
            apply_migrations(db_path)
            repository = SQLiteCodeSandboxExecutionRepository(db_path)

            created = repository.create_execution(
                CodeSandboxExecutionCreatePayload(
                    execution_id="cs-1",
                    execution_mode="sync",
                    runtime_preset="shell",
                    network_policy="disabled",
                    timeout_sec=8,
                    code="echo hi",
                    command=None,
                    stdin=None,
                    inline_files=[],
                    created_at="2026-04-10T00:00:00Z",
                    queued_at="2026-04-10T00:00:00Z",
                    updated_at="2026-04-10T00:00:00Z",
                    provider_name="docker",
                    owner_id="alice",
                    tenant_id="tenant:default",
                    principal_id="principal:alice",
                    auth_scopes=["sandbox:execute"],
                    credential_id="cred-1",
                    auth_mode="api_key",
                )
            )
            self.assertEqual("queued", created.status)

            started = repository.mark_execution_started(
                "cs-1",
                updated_at="2026-04-10T00:00:01Z",
                provider_name="docker",
            )
            assert started is not None
            self.assertEqual("running", started.status)
            self.assertEqual("sync", started.execution_mode)

            seq = repository.append_log_chunk(
                "cs-1",
                created_at="2026-04-10T00:00:01Z",
                stream_name="stdout",
                chunk_text="streaming...\n",
            )
            self.assertEqual(1, seq)

            repository.mark_execution_completed(
                "cs-1",
                updated_at="2026-04-10T00:00:02Z",
                finished_at="2026-04-10T00:00:02Z",
                exit_code=0,
                stdout="ok",
                stderr="",
                timed_out=False,
                error_detail=None,
                output_files=[{"path": "report.txt", "byte_size": 12}],
            )

            record = repository.get_execution("cs-1")
            assert record is not None
            self.assertEqual("completed", record.status)
            self.assertEqual("ok", record.stdout)
            self.assertEqual("docker", record.provider_name)
            self.assertEqual(1, record.last_log_seq)
            self.assertEqual(
                [{"path": "report.txt", "byte_size": 12}], record.output_files
            )

            logs = repository.list_log_chunks("cs-1")
            self.assertEqual(["streaming...\n"], [item.chunk_text for item in logs])

            events = repository.list_execution_events("cs-1")
            self.assertEqual(
                [
                    "execution.queued",
                    "execution.started",
                    "execution.log.stdout",
                    "execution.completed",
                ],
                [event.event_type for event in events],
            )

    def test_repository_marks_queued_execution_cancelled(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            db_path = Path(tmp) / "sandbox.db"
            apply_migrations(db_path)
            repository = SQLiteCodeSandboxExecutionRepository(db_path)

            repository.create_execution(
                CodeSandboxExecutionCreatePayload(
                    execution_id="cs-cancelled",
                    execution_mode="async",
                    runtime_preset="shell",
                    network_policy="disabled",
                    timeout_sec=8,
                    code="echo hi",
                    command=None,
                    stdin=None,
                    inline_files=[],
                    created_at="2026-04-10T00:00:00Z",
                    queued_at="2026-04-10T00:00:00Z",
                    updated_at="2026-04-10T00:00:00Z",
                    provider_name="docker",
                    owner_id="alice",
                    tenant_id="tenant:default",
                    principal_id="principal:alice",
                    auth_scopes=["sandbox:execute"],
                    credential_id="cred-1",
                    auth_mode="api_key",
                )
            )

            repository.mark_execution_cancelled(
                "cs-cancelled",
                updated_at="2026-04-10T00:00:01Z",
                finished_at="2026-04-10T00:00:01Z",
                error_detail="Execution cancelled before start.",
            )

            record = repository.get_execution("cs-cancelled")
            assert record is not None
            self.assertEqual("cancelled", record.status)
            self.assertEqual("2026-04-10T00:00:01Z", record.finished_at)
            self.assertEqual("Execution cancelled before start.", record.error_detail)
            self.assertEqual([], record.output_files)

            events = repository.list_execution_events("cs-cancelled")
            self.assertEqual(
                ["execution.queued", "execution.cancelled"],
                [event.event_type for event in events],
            )


if __name__ == "__main__":
    unittest.main()
