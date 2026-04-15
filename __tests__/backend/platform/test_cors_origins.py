from __future__ import annotations

import unittest

try:
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.testclient import TestClient
except ImportError:  # pragma: no cover - environment without backend deps
    FastAPI = None  # type: ignore[assignment]
    CORSMiddleware = None  # type: ignore[assignment]
    TestClient = None  # type: ignore[assignment]

from backend.platform.config import CORS_ORIGINS


@unittest.skipUnless(
    FastAPI is not None and TestClient is not None and CORSMiddleware is not None,
    "fastapi not installed",
)
class CorsOriginsIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        app = FastAPI()
        app.add_middleware(
            CORSMiddleware,
            allow_origins=CORS_ORIGINS,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        @app.get("/api/health")
        def health() -> dict[str, str]:
            return {"status": "ok"}

        self.client = TestClient(app)

    def test_tauri_desktop_origin_is_allowed_for_preflight(self) -> None:
        response = self.client.options(
            "/api/health",
            headers={
                "Origin": "http://tauri.localhost",
                "Access-Control-Request-Method": "GET",
            },
        )

        self.assertEqual(200, response.status_code)
        self.assertEqual(
            "http://tauri.localhost", response.headers["access-control-allow-origin"]
        )
        self.assertEqual("true", response.headers["access-control-allow-credentials"])


if __name__ == "__main__":
    unittest.main()
