from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.application.code_sandbox import (
    _normalize_request,
    _validate_relative_workspace_path,
    execute_code_sandbox_request,
)
from backend.application.exceptions import CodeSandboxValidationError
from backend.domain.authz_types import AuthorizationContext
from backend.domain.authorization import PrincipalId, TenantId
from backend.models.code_sandbox import CodeSandboxExecRequest, CodeSandboxInlineFile
from backend.services.code_sandbox_runtime import (
    CodeSandboxExecutionCreatePayload,
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


class _FakeRepository:
    def __init__(self) -> None:
        self.record: CodeSandboxExecutionRecord | None = None

    def create_execution(
        self, payload: CodeSandboxExecutionCreatePayload
    ) -> CodeSandboxExecutionRecord:
        self.record = CodeSandboxExecutionRecord(
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
        return self.record

    def get_execution(self, execution_id: str) -> CodeSandboxExecutionRecord | None:
        if self.record is None or self.record.id != execution_id:
            return None
        return self.record


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

        with patch(
            "backend.application.code_sandbox.ensure_code_sandbox_enabled",
            return_value=None,
        ):
            response = execute_code_sandbox_request(
                request=CodeSandboxExecRequest(execution_mode="async", code="echo ok"),
                repository=repository,
                provider=_FakeProvider(),
                dispatcher=dispatcher,
                settings=_settings(),
                auth_context=_auth_context(),
            )

        self.assertEqual("async", response.execution_mode)
        self.assertEqual("queued", response.status)
        self.assertEqual(1, len(dispatcher.calls))

    def test_execute_code_sandbox_request_runs_sync_execution_inline(self) -> None:
        repository = _FakeRepository()
        dispatcher = _FakeDispatcher()

        def _mark_completed(**kwargs: object) -> None:
            _ = kwargs
            assert repository.record is not None
            repository.record = CodeSandboxExecutionRecord(
                **{**repository.record.__dict__, "status": "completed", "exit_code": 0}
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
                settings=_settings(),
                auth_context=_auth_context(),
            )

        execute_sync.assert_called_once()
        self.assertEqual("completed", response.status)
        self.assertEqual(0, response.exit_code)
        self.assertEqual([], dispatcher.calls)


if __name__ == "__main__":
    unittest.main()
