"""GOAT AI — FastAPI entrypoint.

Phase 0: health check + optional React SPA serving.
Run: uvicorn server:app --host 0.0.0.0 --port 8002 --reload
"""
from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from goat_ai.logging_config import configure_logging

configure_logging()
logger = logging.getLogger(__name__)

DIST = Path(__file__).parent / "frontend" / "dist"


def create_app() -> FastAPI:
    """App factory — keeps create/configure separate from module-level side effects."""
    application = FastAPI(
        title="GOAT AI",
        version="0.1.0",
        description="Simon Business School Strategic Intelligence",
    )

    # ── API routes (registered first so they take priority over SPA catch-all) ──
    @application.get("/api/health", tags=["system"])
    async def health() -> dict[str, str]:
        """Liveness probe — returns 200 when the server is up."""
        return {"status": "ok", "stack": "fastapi+react"}

    # ── React SPA (production) ──────────────────────────────────────────────────
    if DIST.is_dir():
        logger.info("Serving React build from %s", DIST)
        application.mount("/", StaticFiles(directory=DIST, html=True), name="spa")
    else:
        logger.info(
            "frontend/dist not found — API-only mode. "
            "Run `cd frontend && npm run build` to enable SPA serving."
        )

    return application


app = create_app()
