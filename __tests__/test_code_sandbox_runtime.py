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
                    runtime_preset="shell",
                    network_policy="disabled",
                    code="echo hi",
                    command=None,
                    stdin=None,
                    inline_files=[],
                    created_at="2026-04-10T00:00:00Z",
                    updated_at="2026-04-10T00:00:00Z",
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
            self.assertEqual(
                [{"path": "report.txt", "byte_size": 12}], record.output_files
            )

            events = repository.list_execution_events("cs-1")
            self.assertEqual(
                ["execution.queued", "execution.started", "execution.completed"],
                [event.event_type for event in events],
            )


if __name__ == "__main__":
    unittest.main()
