"""FastAPI dependency factories (Depends() callables).

Import these in routers; never instantiate services directly in route handlers.
"""

from __future__ import annotations

from fastapi import BackgroundTasks, Depends, HTTPException, Request

from backend.domain.authz_types import AuthorizationContext
from backend.domain.credential_registry import build_local_authorization_context
from backend.api_errors import AUTH_INVALID_API_KEY, build_error_body
from backend.config import get_settings
from backend.services.chat_runtime import (
    ConversationLogger,
    OllamaTitleGenerator,
    SessionRepository,
    SQLiteConversationLogger,
    SQLiteSessionRepository,
    TitleGenerator,
)
from backend.services.workbench_runtime import (
    WorkbenchTaskRepository,
    SQLiteWorkbenchTaskRepository,
)
from backend.services.code_sandbox_runtime import (
    CodeSandboxExecutionRepository,
    SQLiteCodeSandboxExecutionRepository,
)
from backend.services.code_sandbox_provider import (
    DockerSandboxProvider,
    LocalHostProvider,
    SandboxProvider,
)
from backend.services.code_sandbox_execution_service import (
    execute_code_sandbox_execution,
)
from backend.services.background_jobs import (
    BackgroundJobRunner,
    FastAPIBackgroundJobRunner,
    ThreadBackgroundJobRunner,
)
from backend.services.workbench_execution_service import execute_workbench_task
from backend.services.tabular_context import (
    EmbeddedCsvTabularExtractor,
    TabularContextExtractor,
)
from backend.services.safeguard_service import (
    ModeScopedSafeguardService,
    SafeguardService,
)
from backend.application.ports import (
    CodeSandboxExecutionDispatcher,
    WorkbenchTaskDispatcher,
)
from backend.types import LLMClient, Settings
from goat_ai.ollama_client import OllamaService


def get_llm_client(settings: Settings = Depends(get_settings)) -> LLMClient:
    """Return an OllamaService bound to the current settings.

    Returning the Protocol type (LLMClient) allows test code to inject fakes
    via app.dependency_overrides[get_llm_client] = lambda: FakeLLMClient().
    """
    return OllamaService(settings)


def get_conversation_logger(
    settings: Settings = Depends(get_settings),
) -> ConversationLogger:
    """Return the append-only conversation logger bound to current settings."""
    return SQLiteConversationLogger(settings.log_db_path)


def get_session_repository(
    settings: Settings = Depends(get_settings),
) -> SessionRepository:
    """Return the session repository bound to current settings."""
    return SQLiteSessionRepository(settings.log_db_path)


def get_workbench_task_repository(
    settings: Settings = Depends(get_settings),
) -> WorkbenchTaskRepository:
    """Return the workbench task repository bound to current settings."""
    return SQLiteWorkbenchTaskRepository(settings.log_db_path)


def get_code_sandbox_execution_repository(
    settings: Settings = Depends(get_settings),
) -> CodeSandboxExecutionRepository:
    """Return the durable code sandbox execution repository."""
    return SQLiteCodeSandboxExecutionRepository(settings.log_db_path)


def get_code_sandbox_provider(
    settings: Settings = Depends(get_settings),
) -> SandboxProvider:
    """Return the current code sandbox execution provider."""
    if settings.code_sandbox_provider == "localhost":
        return LocalHostProvider(settings)
    return DockerSandboxProvider(settings)


class _BackgroundWorkbenchTaskDispatcher:
    def __init__(
        self,
        *,
        runner: BackgroundJobRunner,
        repository: WorkbenchTaskRepository,
        llm: LLMClient,
        settings: Settings,
    ) -> None:
        self._runner = runner
        self._repository = repository
        self._llm = llm
        self._settings = settings

    def dispatch_task(self, *, task_id: str, request_id: str = "") -> None:
        self._runner.submit(
            name="workbench-task-dispatch",
            target=execute_workbench_task,
            kwargs={
                "task_id": task_id,
                "repository": self._repository,
                "llm": self._llm,
                "settings": self._settings,
                "request_id": request_id,
            },
        )


class _BackgroundCodeSandboxExecutionDispatcher:
    def __init__(
        self,
        *,
        runner: BackgroundJobRunner,
        repository: CodeSandboxExecutionRepository,
        provider: SandboxProvider,
        settings: Settings,
    ) -> None:
        self._runner = runner
        self._repository = repository
        self._provider = provider
        self._settings = settings

    def dispatch_execution(self, *, execution_id: str, request_id: str = "") -> None:
        self._runner.submit(
            name="code-sandbox-execution-dispatch",
            target=execute_code_sandbox_execution,
            kwargs={
                "execution_id": execution_id,
                "repository": self._repository,
                "provider": self._provider,
                "settings": self._settings,
            },
        )


def get_workbench_task_dispatcher(
    background_tasks: BackgroundTasks,
    repository: WorkbenchTaskRepository = Depends(get_workbench_task_repository),
    llm: LLMClient = Depends(get_llm_client),
    settings: Settings = Depends(get_settings),
) -> WorkbenchTaskDispatcher:
    """Return the scheduler that hands accepted workbench tasks to the runtime."""
    return _BackgroundWorkbenchTaskDispatcher(
        runner=FastAPIBackgroundJobRunner(background_tasks=background_tasks),
        repository=repository,
        llm=llm,
        settings=settings,
    )


def get_code_sandbox_execution_dispatcher(
    repository: CodeSandboxExecutionRepository = Depends(
        get_code_sandbox_execution_repository
    ),
    provider: SandboxProvider = Depends(get_code_sandbox_provider),
    settings: Settings = Depends(get_settings),
) -> CodeSandboxExecutionDispatcher:
    """Return the scheduler that hands accepted sandbox runs to the runtime."""
    return _BackgroundCodeSandboxExecutionDispatcher(
        runner=ThreadBackgroundJobRunner(),
        repository=repository,
        provider=provider,
        settings=settings,
    )


def get_authorization_context(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> AuthorizationContext:
    ctx = getattr(request.state, "authorization_context", None)
    if isinstance(ctx, AuthorizationContext):
        return ctx
    if not settings.api_key:
        return build_local_authorization_context()
    raise HTTPException(
        status_code=401,
        detail=build_error_body(
            detail="Invalid or missing API key.",
            code=AUTH_INVALID_API_KEY,
            status_code=401,
        ),
    )


def get_title_generator(llm: LLMClient = Depends(get_llm_client)) -> TitleGenerator:
    """Return the title generator using the same Ollama client as chat (injectable for tests)."""
    return OllamaTitleGenerator(llm)


def get_tabular_context_extractor() -> TabularContextExtractor:
    """Return the tabular context extractor used for chart tool data resolution."""
    return EmbeddedCsvTabularExtractor()


def get_safeguard_service(
    settings: Settings = Depends(get_settings),
) -> SafeguardService | None:
    """Return the active safeguard service, or None when moderation is disabled.

    Controlled by two env vars (see docs/OPERATIONS.md — Safeguard configuration):
      GOAT_SAFEGUARD_ENABLED=false  → always returns None (master kill-switch)
      GOAT_SAFEGUARD_MODE=off       → also returns None
      GOAT_SAFEGUARD_MODE=input_only|output_only|full → returns a ModeScopedSafeguardService

    Returning None is correct: chat_stream_service already guards every safeguard
    call with `if safeguard is None` checks, so None means "allow everything through"
    without any scattered conditionals in the calling code.
    """
    if not settings.safeguard_enabled or settings.safeguard_mode == "off":
        return None
    return ModeScopedSafeguardService(mode=settings.safeguard_mode)
