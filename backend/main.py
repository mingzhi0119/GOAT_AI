"""GOAT AI FastAPI application factory."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.platform.config import CORS_ORIGINS, get_settings
from backend.domain.rate_limit_policy import RateLimitPolicy
from backend.platform.exception_handlers import register_exception_handlers
from backend.platform.http_security import register_http_security
from backend.routers import (
    artifacts,
    chat,
    code_sandbox,
    history,
    knowledge,
    media,
    models,
    system,
    upload,
    workbench,
)
from backend.services.code_sandbox_execution_service import (
    recover_queued_code_sandbox_executions,
    reap_abandoned_running_code_sandbox_executions,
)
from backend.services.background_jobs import ThreadBackgroundJobRunner
from backend.services.code_sandbox_provider import (
    DockerSandboxProvider,
    LocalHostProvider,
)
from backend.services.rate_limiter import StoredSlidingWindowRateLimiter
from backend.services.rate_limit_store import InMemorySlidingWindowRateLimitStore
from backend.services.runtime_persistence import (
    build_code_sandbox_execution_repository,
    build_workbench_task_repository,
    initialize_runtime_metadata_store,
)
from backend.services.workbench_execution_service import recover_workbench_tasks
from goat_ai.config.settings import Settings
from goat_ai.telemetry.latency_metrics import init_latency_metrics
from goat_ai.telemetry.logging_config import configure_logging
from goat_ai.llm.ollama_client import OllamaService
from goat_ai.telemetry.otel_tracing import init_otel_if_enabled, is_otel_enabled

logger = logging.getLogger(__name__)

DIST = Path(__file__).parent.parent / "frontend" / "dist"
APP_VERSION = "1.3.0"
OPENAPI_TAGS = [
    {"name": "system", "description": "Health and server telemetry endpoints."},
    {
        "name": "models",
        "description": "Model discovery endpoints for Ollama-backed chat.",
    },
    {
        "name": "chat",
        "description": "Streaming conversational analysis endpoints.",
    },
    {
        "name": "upload",
        "description": "Tabular file analysis endpoints for CSV/XLSX uploads.",
    },
    {
        "name": "history",
        "description": "Persisted chat session listing and retrieval.",
    },
    {
        "name": "knowledge",
        "description": "Contract-first knowledge ingestion and retrieval endpoints.",
    },
    {"name": "media", "description": "Image uploads for vision-capable chat."},
    {"name": "artifacts", "description": "Download generated chat files."},
    {
        "name": "code_sandbox",
        "description": "Capability-gated isolated code execution.",
    },
    {
        "name": "workbench",
        "description": "Durable workbench task orchestration.",
    },
]


def _build_code_sandbox_provider(
    settings: Settings,
) -> DockerSandboxProvider | LocalHostProvider:
    if settings.code_sandbox_provider == "localhost":
        return LocalHostProvider(settings)
    return DockerSandboxProvider(settings)


def run_workbench_recovery(*, settings: Settings) -> None:
    repository = build_workbench_task_repository(settings)
    recover_workbench_tasks(
        repository=repository,
        llm=OllamaService(settings),
        settings=settings,
    )


def _build_lifespan(settings: Settings):
    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        recovery_runner = ThreadBackgroundJobRunner()

        def run_code_sandbox_recovery() -> None:
            repository = build_code_sandbox_execution_repository(settings)
            provider = _build_code_sandbox_provider(settings)
            reap_abandoned_running_code_sandbox_executions(
                repository=repository,
            )
            recover_queued_code_sandbox_executions(
                repository=repository,
                provider=provider,
                settings=settings,
            )

        recovery_runner.submit(
            name="code-sandbox-recovery",
            target=run_code_sandbox_recovery,
        )
        if settings.feature_agent_workbench_enabled:
            recovery_runner.submit(
                name="workbench-recovery",
                target=run_workbench_recovery,
                kwargs={"settings": settings},
            )
        yield

    return lifespan


def _configure_runtime_services(settings: Settings) -> None:
    initialize_runtime_metadata_store(settings)
    init_latency_metrics(settings.latency_rolling_max_samples)
    init_otel_if_enabled()


def _register_routes(app: FastAPI) -> None:
    app.include_router(models.router, prefix="/api", tags=["models"])
    app.include_router(chat.router, prefix="/api", tags=["chat"])
    app.include_router(upload.router, prefix="/api", tags=["upload"])
    app.include_router(history.router, prefix="/api", tags=["history"])
    app.include_router(knowledge.router, prefix="/api", tags=["knowledge"])
    app.include_router(media.router, prefix="/api", tags=["media"])
    app.include_router(artifacts.router, prefix="/api", tags=["artifacts"])
    app.include_router(system.router, prefix="/api", tags=["system"])
    app.include_router(code_sandbox.router, prefix="/api", tags=["code_sandbox"])
    app.include_router(workbench.router, prefix="/api", tags=["workbench"])

    @app.get("/api/health", tags=["system"], summary="Read service liveness")
    def health() -> dict[str, str]:
        return {"status": "ok", "version": APP_VERSION}


def _mount_spa_if_available(app: FastAPI) -> None:
    if DIST.is_dir():
        logger.info("Serving React SPA from %s", DIST)
        app.mount("/", StaticFiles(directory=DIST, html=True), name="spa")
    else:
        logger.info(
            "frontend/dist not found; running in API-only mode. "
            "Run `cd frontend && npm run build` to enable SPA serving."
        )


def _build_app(
    *,
    settings: Settings,
    enable_runtime_startup: bool,
    serve_spa: bool,
) -> FastAPI:
    lifespan = _build_lifespan(settings) if enable_runtime_startup else None

    app = FastAPI(
        title="GOAT AI",
        version=APP_VERSION,
        description="Simon Business School Strategic Intelligence API",
        lifespan=lifespan,
        openapi_tags=OPENAPI_TAGS,
    )
    app.openapi_version = "3.2.0"

    if enable_runtime_startup:
        _configure_runtime_services(settings)

    register_exception_handlers(app)

    if enable_runtime_startup and is_otel_enabled():
        from backend.platform.otel_middleware import OtelTraceContextMiddleware

        app.add_middleware(OtelTraceContextMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    rate_limit_store = InMemorySlidingWindowRateLimitStore()

    def rate_limiter_factory(
        resolved_settings: Settings,
    ) -> StoredSlidingWindowRateLimiter:
        return StoredSlidingWindowRateLimiter(
            policy=RateLimitPolicy(
                window_sec=resolved_settings.rate_limit_window_sec,
                max_requests=resolved_settings.rate_limit_max_requests,
            ),
            store=rate_limit_store,
        )

    register_http_security(
        app,
        rate_limiter_factory=rate_limiter_factory,
    )

    _register_routes(app)
    if serve_spa:
        _mount_spa_if_available(app)

    return app


def create_contract_app(settings: Settings | None = None) -> FastAPI:
    """Build an app for schema/contract tooling without runtime side effects."""
    resolved_settings = settings or get_settings()
    return _build_app(
        settings=resolved_settings,
        enable_runtime_startup=False,
        serve_spa=False,
    )


def create_app() -> FastAPI:
    """Build and return the configured runtime FastAPI application."""
    configure_logging()
    return _build_app(
        settings=get_settings(),
        enable_runtime_startup=True,
        serve_spa=True,
    )
