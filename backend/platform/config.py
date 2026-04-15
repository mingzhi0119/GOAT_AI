"""Backend configuration - wraps goat_ai Settings and adds HTTP server options.

Delegates to `goat_ai.config.settings.Settings` for shared env vars.
`get_settings()` is LRU-cached so env vars are read exactly once at startup.
"""

from __future__ import annotations

import os
from functools import lru_cache

from goat_ai.config.settings import Settings, load_settings

# Server-only config (not part of the goat_ai shared layer).
_legacy_backend_port = os.environ.get("GOAT_PORT", "").strip()
BACKEND_PORT: int = int(
    os.environ.get("GOAT_SERVER_PORT", _legacy_backend_port or "62606")
)
BACKEND_HOST: str = os.environ.get("GOAT_HOST", "0.0.0.0")

# Comma-separated list of allowed CORS origins.
# Defaults keep the React dev server and packaged desktop origins working.
CORS_ORIGINS: list[str] = [
    o.strip()
    for o in os.environ.get(
        "GOAT_CORS_ORIGINS",
        ",".join(
            [
                "http://localhost:3000",
                "http://tauri.localhost",
                "http://asset.localhost",
                "https://tauri.localhost",
                "https://asset.localhost",
                "tauri://localhost",
                "asset://localhost",
            ]
        ),
    ).split(",")
    if o.strip()
]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached Settings instance (reads env vars once at first call).

    Raises SystemExit with a clear message if required env vars are invalid.
    """
    try:
        return load_settings()
    except Exception as exc:  # pragma: no cover
        raise SystemExit(f"[GOAT AI] Invalid configuration: {exc}") from exc
