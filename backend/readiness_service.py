"""Readiness checks: SQLite + optional Ollama probe."""
from __future__ import annotations

import logging
import sqlite3
from typing import Any

import requests

from goat_ai.config import Settings

logger = logging.getLogger(__name__)


def evaluate_readiness(settings: Settings) -> tuple[dict[str, Any], int]:
    """Return ``(body, http_status)`` where status is 200 or 503."""
    checks: dict[str, Any] = {}
    ready = True

    checks["settings"] = {"ok": True}

    try:
        conn = sqlite3.connect(str(settings.log_db_path), timeout=5.0)
        try:
            conn.execute("SELECT 1")
        finally:
            conn.close()
        checks["sqlite"] = {"ok": True, "path": str(settings.log_db_path)}
    except Exception as exc:
        ready = False
        logger.error(
            "Readiness SQLite check failed",
            extra={
                "event": "readiness_sqlite_failed",
                "component": "readiness_service",
                "db_path": str(settings.log_db_path),
                "code": "SQLITE_READINESS_FAILED",
            },
            exc_info=True,
        )
        checks["sqlite"] = {"ok": False, "error": str(exc)}

    if settings.ready_skip_ollama_probe:
        checks["ollama"] = {"ok": True, "skipped": True}
    else:
        url = f"{settings.ollama_base_url}/api/tags"
        try:
            response = requests.get(url, timeout=2.0)
            response.raise_for_status()
            checks["ollama"] = {"ok": True, "url": url, "http_status": response.status_code}
        except Exception as exc:
            ready = False
            logger.error(
                "Readiness Ollama probe failed",
                extra={
                    "event": "readiness_ollama_failed",
                    "component": "readiness_service",
                    "url": url,
                    "code": "OLLAMA_READINESS_FAILED",
                },
                exc_info=True,
            )
            checks["ollama"] = {"ok": False, "url": url, "error": str(exc)}

    body: dict[str, Any] = {"ready": ready, "checks": checks}
    return body, (200 if ready else 503)
