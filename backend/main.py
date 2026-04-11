"""GOAT AI FastAPI application factory."""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.config import CORS_ORIGINS, get_settings
from backend.domain.rate_limit_policy import RateLimitPolicy
from backend.exception_handlers import register_exception_handlers
from backend.http_security import register_http_security
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
from backend.services import log_service
from backend.services.rate_limit_store import InMemorySlidingWindowRateLimitStore
from goat_ai.config import Settings
from goat_ai.latency_metrics import init_latency_metrics
from goat_ai.logging_config import configure_logging
from goat_ai.otel_tracing import init_otel_if_enabled, is_otel_enabled

configure_logging()
logger = logging.getLogger(__name__)

DIST = Path(__file__).parent.parent / "frontend" / "dist"


def create_app() -> FastAPI:
    """Build and return the configured FastAPI application."""
    app = FastAPI(
        title="GOAT AI",
        version="1.2.0",
        description="Simon Business School Strategic Intelligence API",
        openapi_tags=[
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
        ],
    )
    app.openapi_version = "3.2.0"

    settings = get_settings()
    log_service.init_db(settings.log_db_path)
    init_latency_metrics(settings.latency_rolling_max_samples)
    init_otel_if_enabled()

    register_exception_handlers(app)

    if is_otel_enabled():
        from backend.otel_middleware import OtelTraceContextMiddleware

        app.add_middleware(OtelTraceContextMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    rate_limit_store = InMemorySlidingWindowRateLimitStore()

    def rate_limit_policy_factory(settings: Settings) -> RateLimitPolicy:
        return RateLimitPolicy(
            window_sec=settings.rate_limit_window_sec,
            max_requests=settings.rate_limit_max_requests,
        )

    register_http_security(
        app,
        rate_limit_policy_factory=rate_limit_policy_factory,
        rate_limit_store=rate_limit_store,
    )

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
        return {"status": "ok", "version": "1.2.0"}

    if DIST.is_dir():
        logger.info("Serving React SPA from %s", DIST)
        app.mount("/", StaticFiles(directory=DIST, html=True), name="spa")
    else:
        logger.info(
            "frontend/dist not found; running in API-only mode. "
            "Run `cd frontend && npm run build` to enable SPA serving."
        )

    return app


app = create_app()
