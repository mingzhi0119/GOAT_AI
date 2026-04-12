from __future__ import annotations

import tempfile
from pathlib import Path

from backend.services.code_sandbox_execution_service import (
    recover_queued_code_sandbox_executions,
)
from backend.services.code_sandbox_provider import (
    SandboxProviderRequest,
    SandboxProviderResult,
)
from backend.services.code_sandbox_runtime import (
    CodeSandboxExecutionCreatePayload,
    SQLiteCodeSandboxExecutionRepository,
)
from backend.services.db_migrations import apply_migrations
from goat_ai.config.settings import Settings


class _FakeSandboxProvider:
    provider_name = "docker"
    isolation_level = "container"
    network_policy_enforced = True

    def run_stream(self, request: SandboxProviderRequest):
        _ = request
        yield SandboxProviderResult(
            provider_name=self.provider_name,
            exit_code=0,
            stdout="recovered ok\n",
            stderr="",
            timed_out=False,
            error_detail=None,
            output_files=[],
        )


def _settings(root: Path) -> Settings:
    return Settings(
        ollama_base_url="http://127.0.0.1:11434",
        generate_timeout=120,
        max_upload_mb=20,
        max_upload_bytes=20 * 1024 * 1024,
        max_dataframe_rows=50000,
        use_chat_api=True,
        system_prompt="t",
        app_root=root,
        logo_svg=root / "logo.svg",
        log_db_path=root / "sandbox.db",
    )


def test_recover_queued_code_sandbox_executions_completes_persisted_runs() -> None:
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        root = Path(tmp)
        settings = _settings(root)
        apply_migrations(settings.log_db_path)
        repository = SQLiteCodeSandboxExecutionRepository(settings.log_db_path)
        repository.create_execution(
            CodeSandboxExecutionCreatePayload(
                execution_id="cs-recover-1",
                execution_mode="async",
                runtime_preset="shell",
                network_policy="disabled",
                timeout_sec=8,
                code="echo recover",
                command=None,
                stdin=None,
                inline_files=[],
                created_at="2026-04-11T00:00:00Z",
                queued_at="2026-04-11T00:00:00Z",
                updated_at="2026-04-11T00:00:00Z",
                provider_name="docker",
            )
        )

        recovered = recover_queued_code_sandbox_executions(
            repository=repository,
            provider=_FakeSandboxProvider(),
            settings=settings,
        )

        assert recovered == ["cs-recover-1"]
        record = repository.get_execution("cs-recover-1")
        assert record is not None
        assert record.status == "completed"
        assert record.stdout == "recovered ok\n"
