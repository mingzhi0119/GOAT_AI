from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.application.code_sandbox import (
    _normalize_request,
    _validate_relative_workspace_path,
    cancel_code_sandbox_execution,
    execute_code_sandbox_request,
    retry_code_sandbox_execution,
)
from backend.application.exceptions import (
    CodeSandboxExecutionConflictError,
    CodeSandboxValidationError,
)
from backend.domain.authz_types import AuthorizationContext
from backend.domain.authorization import PrincipalId, TenantId
from backend.models.code_sandbox import CodeSandboxExecRequest, CodeSandboxInlineFile
from backend.services.code_sandbox_runtime import (
    CodeSandboxExecutionCreatePayload,
    CodeSandboxExecutionEventRecord,
    CodeSandboxExecutionRecord,
)
from goat_ai.config.settings import Settings


def _settings() -> Settings:
    root = Path(tempfile.gettempdir()) / "goat-ai-code-sandbox-tests"
    return Settings(
        ollama_base_url="http://127.0.0.1:11434",
        generate_timeout=120,
        max_upload_mb=20,
        max_upload_bytes=20 * 1024 * 1024,
        max_dataframe_rows=50000,
        use_chat_api=True,
        system_prompt="test",
        app_root=root,
        logo_svg=root / "logo.svg",
        log_db_path=root / "chat_logs.db",
        feature_code_sandbox_enabled=True,
    )


def _auth_context() -> AuthorizationContext:
    return AuthorizationContext(
        principal_id=PrincipalId("principal-1"),
        tenant_id=TenantId("tenant-1"),
        scopes=frozenset({"sandbox:execute"}),
        credential_id="cred-1",
        legacy_owner_id="owner-1",
        auth_mode="api_key",
    )


class _FakeProvider:
    provider_name = "docker"


class _FakeDispatcher:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def dispatch_execution(self, *, execution_id: str, request_id: str = "") -> None:
        _ = request_id
        self.calls.append(execution_id)


class _FakeSupervisor:
    def __init__(self, repository: _FakeRepository | None = None) -> None:
        self.repository = repository
        self.cancelled_ids: set[str] = set()

    def register_execution(self, *, execution_id: str):
        return lambda: execution_id in self.cancelled_ids

    def request_cancel(self, *, execution_id: str) -> None:
        self.cancelled_ids.add(execution_id)
        if self.repository is None:
            return
        record = self.repository.records.get(execution_id)
        if record is None or record.status != "running":
            return
        self.repository.records[execution_id] = CodeSandboxExecutionRecord(
            **{
                **record.__dict__,
                "status": "cancelled",
                "updated_at": "2026-04-10T00:00:03Z",
                "finished_at": "2026-04-10T00:00:03Z",
                "error_detail": "Execution cancelled by request.",
                "output_files": record.output_files or [],
            }
        )
        self.repository.append_execution_event(
            execution_id,
            event_type="execution.cancelled",
            created_at="2026-04-10T00:00:03Z",
            status="cancelled",
            message="Execution cancelled by request.",
            metadata=None,
        )

    def release_execution(self, *, execution_id: str) -> None:
        _ = execution_id


class _FakeRepository:
    def __init__(self) -> None:
        self.records: dict[str, CodeSandboxExecutionRecord] = {}
        self.events: dict[str, list[CodeSandboxExecutionEventRecord]] = {}

    def create_execution(
        self, payload: CodeSandboxExecutionCreatePayload
    ) -> CodeSandboxExecutionRecord:
        record = CodeSandboxExecutionRecord(
            id=payload.execution_id,
            status=payload.status,
            execution_mode=payload.execution_mode,
            runtime_preset=payload.runtime_preset,
            network_policy=payload.network_policy,
            timeout_sec=payload.timeout_sec,
            code=payload.code,
            command=payload.command,
            stdin=payload.stdin,
            inline_files=payload.inline_files,
            created_at=payload.created_at,
            queued_at=payload.queued_at,
            updated_at=payload.updated_at,
            provider_name=payload.provider_name,
            owner_id=payload.owner_id,
            tenant_id=payload.tenant_id,
            principal_id=payload.principal_id,
            auth_scopes=payload.auth_scopes,
            credential_id=payload.credential_id,
            auth_mode=payload.auth_mode,
        )
        self.records[record.id] = record
        self.events.setdefault(record.id, []).append(
            CodeSandboxExecutionEventRecord(
                execution_id=record.id,
                sequence=1,
                event_type="execution.queued",
                created_at=payload.created_at,
                status=record.status,
                message="Execution accepted.",
                metadata={
                    "execution_mode": payload.execution_mode,
                    "network_policy": payload.network_policy,
                    "runtime_preset": payload.runtime_preset,
                },
            )
        )
        return record

    def mark_execution_cancelled(
        self,
        execution_id: str,
        *,
        updated_at: str,
        finished_at: str,
        error_detail: str,
    ) -> None:
        record = self.records.get(execution_id)
        if record is None or record.status != "queued":
            return
        self.records[execution_id] = CodeSandboxExecutionRecord(
            **{
                **record.__dict__,
                "status": "cancelled",
                "updated_at": updated_at,
                "finished_at": finished_at,
                "error_detail": error_detail,
                "timed_out": False,
                "output_files": record.output_files or [],
            }
        )
        self.append_execution_event(
            execution_id,
            event_type="execution.cancelled",
            created_at=finished_at,
            status="cancelled",
            message="Execution cancelled before start.",
            metadata=None,
        )

    def append_execution_event(
        self,
        execution_id: str,
        *,
        event_type: str,
        created_at: str,
        status: str | None,
        message: str | None,
        metadata: dict[str, object] | None,
    ) -> None:
        sequence = len(self.events.setdefault(execution_id, [])) + 1
        self.events[execution_id].append(
            CodeSandboxExecutionEventRecord(
                execution_id=execution_id,
                sequence=sequence,
                event_type=event_type,
                created_at=created_at,
                status=status,
                message=message,
                metadata=metadata,
            )
        )

    def get_execution(self, execution_id: str) -> CodeSandboxExecutionRecord | None:
        return self.records.get(execution_id)


def _seed_record(
    repository: _FakeRepository,
    *,
    execution_id: str = "cs-seeded",
    status: str = "queued",
    execution_mode: str = "async",
    owner_id: str = "owner-1",
    tenant_id: str = "tenant-1",
    principal_id: str = "principal-1",
    auth_scopes: list[str] | None = None,
    credential_id: str = "cred-seeded",
    auth_mode: str = "api_key",
    provider_name: str = "docker",
) -> CodeSandboxExecutionRecord:
    record = CodeSandboxExecutionRecord(
        id=execution_id,
        status=status,
        execution_mode=execution_mode,
        runtime_preset="shell",
        network_policy="disabled",
        timeout_sec=8,
        code="echo ok",
        command="printf retry",
        stdin=None,
        inline_files=[{"filename": "inputs/data.txt", "content": "seed"}],
        created_at="2026-04-10T00:00:00Z",
        queued_at="2026-04-10T00:00:00Z",
        updated_at="2026-04-10T00:00:00Z",
        started_at="2026-04-10T00:00:01Z" if status != "queued" else None,
        finished_at="2026-04-10T00:00:02Z"
        if status in {"completed", "failed", "denied", "cancelled"}
        else None,
        exit_code=0 if status == "completed" else None,
        stdout="done" if status == "completed" else "",
        stderr="bad exit" if status == "failed" else "",
        timed_out=False,
        error_detail="denied" if status == "denied" else None,
        output_files=[],
        provider_name=provider_name,
        owner_id=owner_id,
        tenant_id=tenant_id,
        principal_id=principal_id,
        auth_scopes=list(auth_scopes or ["sandbox:execute"]),
        credential_id=credential_id,
        auth_mode=auth_mode,
    )
    repository.records[execution_id] = record
    repository.events[execution_id] = []
    return record


class ApplicationCodeSandboxTests(unittest.TestCase):
    def test_validate_relative_workspace_path_accepts_safe_relative_paths(self) -> None:
        self.assertEqual(
            "outputs/report.txt",
            _validate_relative_workspace_path("outputs/report.txt"),
        )

    def test_validate_relative_workspace_path_rejects_absolute_or_traversing_paths(
        self,
    ) -> None:
        for raw in ("", "/tmp/report.txt", "../secret.txt", "nested/../secret.txt"):
            with self.assertRaises(CodeSandboxValidationError):
                _validate_relative_workspace_path(raw)

    def test_normalize_request_trims_inputs_and_normalizes_inline_files(self) -> None:
        normalized = _normalize_request(
            request=CodeSandboxExecRequest(
                code="  echo ok  ",
                command="  python script.py  ",
                stdin="hello",
                files=[
                    CodeSandboxInlineFile(filename="nested/input.txt", content="data")
                ],
            ),
            settings=_settings(),
            execution_id="cs-1",
        )

        self.assertEqual("sync", normalized.execution_mode)
        self.assertEqual("echo ok", normalized.provider_request.code)
        self.assertEqual("python script.py", normalized.provider_request.command)
        self.assertEqual(
            [{"filename": "nested/input.txt", "content": "data"}],
            normalized.provider_request.inline_files,
        )

    def test_execute_code_sandbox_request_dispatches_async_execution(self) -> None:
        repository = _FakeRepository()
        dispatcher = _FakeDispatcher()
        supervisor = _FakeSupervisor()

        with patch(
            "backend.application.code_sandbox.ensure_code_sandbox_enabled",
            return_value=None,
        ):
            response = execute_code_sandbox_request(
                request=CodeSandboxExecRequest(execution_mode="async", code="echo ok"),
                repository=repository,
                provider=_FakeProvider(),
                dispatcher=dispatcher,
                supervisor=supervisor,
                settings=_settings(),
                auth_context=_auth_context(),
            )

        self.assertEqual("async", response.execution_mode)
        self.assertEqual("queued", response.status)
        self.assertEqual(1, len(dispatcher.calls))

    def test_execute_code_sandbox_request_runs_sync_execution_inline(self) -> None:
        repository = _FakeRepository()
        dispatcher = _FakeDispatcher()
        supervisor = _FakeSupervisor()

        def _mark_completed(**kwargs: object) -> None:
            execution_id = str(kwargs["execution_id"])
            record = repository.records[execution_id]
            repository.records[execution_id] = CodeSandboxExecutionRecord(
                **{**record.__dict__, "status": "completed", "exit_code": 0}
            )

        with (
            patch(
                "backend.application.code_sandbox.ensure_code_sandbox_enabled",
                return_value=None,
            ),
            patch(
                "backend.application.code_sandbox.execute_code_sandbox_execution",
                side_effect=_mark_completed,
            ) as execute_sync,
        ):
            response = execute_code_sandbox_request(
                request=CodeSandboxExecRequest(execution_mode="sync", code="echo ok"),
                repository=repository,
                provider=_FakeProvider(),
                dispatcher=dispatcher,
                supervisor=supervisor,
                settings=_settings(),
                auth_context=_auth_context(),
            )

        execute_sync.assert_called_once()
        self.assertEqual("completed", response.status)
        self.assertEqual(0, response.exit_code)
        self.assertEqual([], dispatcher.calls)

    def test_cancel_code_sandbox_execution_marks_queued_execution_cancelled(
        self,
    ) -> None:
        repository = _FakeRepository()
        supervisor = _FakeSupervisor(repository)
        _seed_record(repository, status="queued")

        with patch(
            "backend.application.code_sandbox.ensure_code_sandbox_enabled",
            return_value=None,
        ):
            response = cancel_code_sandbox_execution(
                execution_id="cs-seeded",
                repository=repository,
                supervisor=supervisor,
                settings=_settings(),
                auth_context=_auth_context(),
            )

        self.assertEqual("cancelled", response.status)
        self.assertEqual("Execution cancelled before start.", response.error_detail)
        self.assertIsNotNone(response.finished_at)
        self.assertEqual(
            "execution.cancelled",
            repository.events["cs-seeded"][-1].event_type,
        )

    def test_cancel_code_sandbox_execution_marks_running_execution_cancelled(
        self,
    ) -> None:
        repository = _FakeRepository()
        supervisor = _FakeSupervisor(repository)
        _seed_record(repository, status="running")

        with patch(
            "backend.application.code_sandbox.ensure_code_sandbox_enabled",
            return_value=None,
        ):
            response = cancel_code_sandbox_execution(
                execution_id="cs-seeded",
                repository=repository,
                supervisor=supervisor,
                settings=_settings(),
                auth_context=_auth_context(),
            )

        self.assertEqual("cancelled", response.status)
        self.assertEqual("Execution cancelled by request.", response.error_detail)
        self.assertEqual(
            ["execution.cancel_requested", "execution.cancelled"],
            [event.event_type for event in repository.events["cs-seeded"]],
        )

    def test_cancel_code_sandbox_execution_rejects_terminal_state(self) -> None:
        repository = _FakeRepository()
        supervisor = _FakeSupervisor(repository)
        _seed_record(repository, status="completed")

        with (
            patch(
                "backend.application.code_sandbox.ensure_code_sandbox_enabled",
                return_value=None,
            ),
            self.assertRaises(CodeSandboxExecutionConflictError),
        ):
            cancel_code_sandbox_execution(
                execution_id="cs-seeded",
                repository=repository,
                supervisor=supervisor,
                settings=_settings(),
                auth_context=_auth_context(),
            )

    def test_retry_code_sandbox_execution_reuses_original_auth_snapshot(self) -> None:
        repository = _FakeRepository()
        seeded = _seed_record(
            repository,
            status="completed",
            execution_mode="async",
            owner_id="owner-original",
            tenant_id="tenant-original",
            principal_id="principal-original",
            auth_scopes=["sandbox:execute", "history:read"],
            credential_id="cred-original",
            auth_mode="scoped_key",
        )
        dispatcher = _FakeDispatcher()
        supervisor = _FakeSupervisor()
        current_auth = AuthorizationContext(
            principal_id=PrincipalId("principal-original"),
            tenant_id=TenantId("tenant-original"),
            scopes=frozenset({"sandbox:execute"}),
            credential_id="cred-current",
            legacy_owner_id="owner-original",
            auth_mode="api_key",
        )

        with patch(
            "backend.application.code_sandbox.ensure_code_sandbox_enabled",
            return_value=None,
        ):
            response = retry_code_sandbox_execution(
                execution_id=seeded.id,
                repository=repository,
                provider=_FakeProvider(),
                dispatcher=dispatcher,
                supervisor=supervisor,
                settings=_settings(),
                auth_context=current_auth,
            )

        self.assertEqual("async", response.execution_mode)
        self.assertEqual("queued", response.status)
        self.assertEqual(1, len(dispatcher.calls))
        retried = repository.get_execution(response.execution_id)
        assert retried is not None
        self.assertNotEqual(seeded.id, retried.id)
        self.assertEqual("owner-original", retried.owner_id)
        self.assertEqual("tenant-original", retried.tenant_id)
        self.assertEqual("principal-original", retried.principal_id)
        self.assertEqual(["sandbox:execute", "history:read"], retried.auth_scopes)
        self.assertEqual("cred-original", retried.credential_id)
        self.assertEqual("scoped_key", retried.auth_mode)
        self.assertEqual(
            "execution.retry_requested",
            repository.events[seeded.id][-1].event_type,
        )
        self.assertEqual(
            seeded.id,
            repository.events[retried.id][-1].metadata["source_execution_id"],
        )

    def test_retry_code_sandbox_execution_runs_sync_retry_inline(self) -> None:
        repository = _FakeRepository()
        _seed_record(repository, status="failed", execution_mode="sync")
        dispatcher = _FakeDispatcher()
        supervisor = _FakeSupervisor()

        def _complete_retry(**kwargs: object) -> None:
            execution_id = str(kwargs["execution_id"])
            record = repository.records[execution_id]
            repository.records[execution_id] = CodeSandboxExecutionRecord(
                **{
                    **record.__dict__,
                    "status": "completed",
                    "exit_code": 0,
                    "stdout": "retry ok",
                    "stderr": "",
                    "finished_at": "2026-04-10T00:00:03Z",
                    "updated_at": "2026-04-10T00:00:03Z",
                }
            )

        with (
            patch(
                "backend.application.code_sandbox.ensure_code_sandbox_enabled",
                return_value=None,
            ),
            patch(
                "backend.application.code_sandbox.execute_code_sandbox_execution",
                side_effect=_complete_retry,
            ) as execute_sync,
        ):
            response = retry_code_sandbox_execution(
                execution_id="cs-seeded",
                repository=repository,
                provider=_FakeProvider(),
                dispatcher=dispatcher,
                supervisor=supervisor,
                settings=_settings(),
                auth_context=_auth_context(),
            )

        execute_sync.assert_called_once()
        self.assertEqual("completed", response.status)
        self.assertEqual("retry ok", response.stdout)
        self.assertEqual([], dispatcher.calls)

    def test_retry_code_sandbox_execution_rejects_non_terminal_state(self) -> None:
        repository = _FakeRepository()
        supervisor = _FakeSupervisor()
        _seed_record(repository, status="running")

        with (
            patch(
                "backend.application.code_sandbox.ensure_code_sandbox_enabled",
                return_value=None,
            ),
            self.assertRaises(CodeSandboxExecutionConflictError),
        ):
            retry_code_sandbox_execution(
                execution_id="cs-seeded",
                repository=repository,
                provider=_FakeProvider(),
                dispatcher=_FakeDispatcher(),
                supervisor=supervisor,
                settings=_settings(),
                auth_context=_auth_context(),
            )


if __name__ == "__main__":
    unittest.main()
