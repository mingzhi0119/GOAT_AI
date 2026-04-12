"""GOAT AI — uvicorn entrypoint.

Delegates entirely to the backend package so this file stays a thin alias.

Run:
    python3 -m uvicorn server:app --host 0.0.0.0 --port 62606 [--reload]
"""

from backend.main import app  # noqa: F401  (re-exported for uvicorn)

__all__ = ["app"]
