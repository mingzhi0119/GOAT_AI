"""GOAT AI FastAPI application factory."""
from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.config import CORS_ORIGINS, get_settings
from backend.http_security import register_http_security
from backend.routers import chat, history, models, system, upload
from backend.services import log_service
from goat_ai.latency_metrics import init_latency_metrics
from goat_ai.logging_config import configure_logging

configure_logging()
logger = logging.getLogger(__name__)

DIST = Path(__file__).parent.parent / "frontend" / "dist"


def create_app() -> FastAPI:
    """Build and return the configured FastAPI application."""
    app = FastAPI(
        title="GOAT AI",
        version="1.0.0",
        description="Simon Business School Strategic Intelligence API",
        openapi_tags=[
            {"name": "system", "description": "Health and server telemetry endpoints."},
            {"name": "models", "description": "Model discovery endpoints for Ollama-backed chat."},
            {"name": "chat", "description": "Streaming conversational analysis endpoints."},
            {"name": "upload", "description": "Tabular file analysis endpoints for CSV/XLSX uploads."},
            {"name": "history", "description": "Persisted chat session listing and retrieval."},
        ],
    )
    app.openapi_version = "3.2.0"

    settings = get_settings()
    log_service.init_db(settings.log_db_path)
    init_latency_metrics(settings.latency_rolling_max_samples)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_http_security(app)

    app.include_router(models.router, prefix="/api", tags=["models"])
    app.include_router(chat.router, prefix="/api", tags=["chat"])
    app.include_router(upload.router, prefix="/api", tags=["upload"])
    app.include_router(history.router, prefix="/api", tags=["history"])
    app.include_router(system.router, prefix="/api", tags=["system"])

    @app.get("/api/health", tags=["system"], summary="Read service liveness")
    def health() -> dict[str, str]:
        return {"status": "ok", "version": "1.0.0"}

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
