"""Smoke tests against the full app (SQLite + TestClient)."""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.integration


def test_health_ok(app_client: object) -> None:
    from fastapi.testclient import TestClient

    assert isinstance(app_client, TestClient)
    response = app_client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body.get("status") == "ok"


def test_ready_sqlite_only(app_client: object) -> None:
    from fastapi.testclient import TestClient

    assert isinstance(app_client, TestClient)
    response = app_client.get("/api/ready")
    assert response.status_code == 200
    body = response.json()
    assert body.get("ready") is True
    checks = body.get("checks") or {}
    ollama = checks.get("ollama") or {}
    assert ollama.get("skipped") is True
