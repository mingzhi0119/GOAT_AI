"""Backend configuration — wraps goat_ai Settings and adds HTTP server options.

Reads the same env vars as the Streamlit layer for full backward compatibility.
`get_settings()` is LRU-cached so env vars are read exactly once at startup.
"""
from __future__ import annotations

import os
from functools import lru_cache

from goat_ai.config import Settings, load_settings

# ── Server-only config (not part of goat_ai shared layer) ────────────────────
BACKEND_PORT: int = int(os.environ.get("GOAT_PORT", "8002"))
BACKEND_HOST: str = os.environ.get("GOAT_HOST", "0.0.0.0")

# Comma-separated list of allowed CORS origins (dev: React dev server on :3000)
CORS_ORIGINS: list[str] = [
    o.strip()
    for o in os.environ.get("GOAT_CORS_ORIGINS", "http://localhost:3000").split(",")
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
