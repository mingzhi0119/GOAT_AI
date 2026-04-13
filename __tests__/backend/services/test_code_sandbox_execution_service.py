from __future__ import annotations

import tempfile
import threading
import time
from pathlib import Path

from backend.services.code_sandbox_execution_service import (
    execute_code_sandbox_execution,
    recover_queued_code_sandbox_executions,
    reap_abandoned_running_code_sandbox_executions,
)
from backend.services.code_sandbox_provider import (
    SandboxProviderLogChunk,
    SandboxProviderRequest,
    SandboxProviderResult,
)
from backend.services.code_sandbox_runtime import (
    CodeSandboxExecutionCreatePayload,
    SQLiteCodeSandboxExecutionRepository,
)
from backend.services.code_sandbox_supervisor import InProcessCodeSandboxSupervisor
from backend.services.db_migrations import apply_migrations
from goat_ai.config.settings import Settings


class _FakeSandboxProvider:
    provider_name = "docker"
    isolation_level = "container"
    network_policy_enforced = True

    def run_stream(
        self,
        request: SandboxProviderRequest,
        *,
        cancel_requested=None,
    ):
        _ = request
        yield SandboxProviderResult(
            provider_name=self.provider_name,
            exit_code=0,
            stdout="recovered ok\n",
            stderr="",
            timed_out=False,
            cancelled=False,
            error_detail=None,
            output_files=[],
        )


class _SlowCancellableProvider:
    provider_name = "docker"
    isolation_level = "container"
    network_policy_enforced = True

    def run_stream(
        self,
        request: SandboxProviderRequest,
        *,
        cancel_requested=None,
    ):
        _ = request
        yield SandboxProviderLogChunk(
            stream_name="stdout",
            created_at="2026-04-11T00:00:01Z",
            text="starting\n",
        )
        deadline = time.monotonic() + 1.0
        while time.monotonic() < deadline:
            if cancel_requested is not None and cancel_requested():
                yield SandboxProviderResult(
                    provider_name=self.provider_name,
                    exit_code=None,
                    stdout="",
                    stderr="",
                    timed_out=False,
                    cancelled=True,
                    error_detail="Execution cancelled by request.",
                    output_files=[],
                )
                return
            time.sleep(0.02)
        yield SandboxProviderResult(
            provider_name=self.provider_name,
            exit_code=0,
            stdout="finished\n",
            stderr="",
            timed_out=False,
            cancelled=False,
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


def test_execute_code_sandbox_execution_marks_running_execution_cancelled() -> None:
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        root = Path(tmp)
        settings = _settings(root)
        apply_migrations(settings.log_db_path)
        repository = SQLiteCodeSandboxExecutionRepository(settings.log_db_path)
        repository.create_execution(
            CodeSandboxExecutionCreatePayload(
                execution_id="cs-running-cancel",
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
        supervisor = InProcessCodeSandboxSupervisor()
        worker = threading.Thread(
            target=execute_code_sandbox_execution,
            kwargs={
                "execution_id": "cs-running-cancel",
                "repository": repository,
                "provider": _SlowCancellableProvider(),
                "supervisor": supervisor,
                "settings": settings,
                "raise_errors": False,
            },
        )
        worker.start()
        deadline = time.monotonic() + 2.0
        record = repository.get_execution("cs-running-cancel")
        while record is not None and record.status != "running":
            if time.monotonic() >= deadline:
                break
            time.sleep(0.02)
            record = repository.get_execution("cs-running-cancel")

        supervisor.request_cancel(execution_id="cs-running-cancel")
        worker.join(timeout=2.0)

        record = repository.get_execution("cs-running-cancel")
        assert record is not None
        assert record.status == "cancelled"
        assert record.error_detail == "Execution cancelled by request."
        events = repository.list_execution_events("cs-running-cancel")
        assert [event.event_type for event in events] == [
            "execution.queued",
            "execution.started",
            "execution.log.stdout",
            "execution.cancelled",
        ]


def test_reap_abandoned_running_code_sandbox_executions_marks_terminal_state() -> None:
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        root = Path(tmp)
        settings = _settings(root)
        apply_migrations(settings.log_db_path)
        repository = SQLiteCodeSandboxExecutionRepository(settings.log_db_path)
        repository.create_execution(
            CodeSandboxExecutionCreatePayload(
                execution_id="cs-abandoned-running",
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
        repository.mark_execution_started(
            "cs-abandoned-running",
            updated_at="2026-04-11T00:00:01Z",
            provider_name="docker",
        )

        recovered = reap_abandoned_running_code_sandbox_executions(
            repository=repository,
            recovered_at="2026-04-11T00:00:02Z",
        )

        assert recovered == ["cs-abandoned-running"]
        record = repository.get_execution("cs-abandoned-running")
        assert record is not None
        assert record.status == "failed"
        assert (
            record.error_detail
            == "Execution interrupted by runtime restart before completion."
        )
        events = repository.list_execution_events("cs-abandoned-running")
        assert [event.event_type for event in events] == [
            "execution.queued",
            "execution.started",
            "execution.recovered_after_restart",
            "execution.failed",
        ]
