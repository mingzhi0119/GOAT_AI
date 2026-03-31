"""GOAT AI — FastAPI application factory.

Usage:
    python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8002
    # or via the project root alias:
    python3 -m uvicorn server:app --host 0.0.0.0 --port 8002
"""
from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.config import CORS_ORIGINS, get_settings
from backend.routers import chat, history, models, upload
from backend.services import log_service
from goat_ai.logging_config import configure_logging

configure_logging()
logger = logging.getLogger(__name__)

DIST = Path(__file__).parent.parent / "frontend" / "dist"


def create_app() -> FastAPI:
    """Build and return the configured FastAPI application."""
    app = FastAPI(
        title="GOAT AI",
        version="1.0.0",
        description="Simon Business School — Strategic Intelligence API",
        # Hide docs in production by setting docs_url=None; keep open for now.
    )

    # ── Initialise chat log DB on startup ─────────────────────────────────────
    log_service.init_db(get_settings().log_db_path)

    # ── CORS (allows React dev server on :3000 to call the API on :8002) ──────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── API routes (must be registered before the SPA catch-all) ─────────────
    app.include_router(models.router, prefix="/api", tags=["models"])
    app.include_router(chat.router,   prefix="/api", tags=["chat"])
    app.include_router(upload.router, prefix="/api", tags=["upload"])
    app.include_router(history.router, prefix="/api", tags=["history"])

    # ── Health probe (quick liveness check, no deps) ──────────────────────────
    @app.get("/api/health", tags=["system"])
    def health() -> dict[str, str]:
        return {"status": "ok", "version": "1.0.0"}

    # ── React SPA (production: built dist/ served as static files) ────────────
    if DIST.is_dir():
        logger.info("Serving React SPA from %s", DIST)
        app.mount("/", StaticFiles(directory=DIST, html=True), name="spa")
    else:
        logger.info(
            "frontend/dist not found — API-only mode. "
            "Run `cd frontend && npm run build` to enable SPA serving."
        )

    return app


app = create_app()
