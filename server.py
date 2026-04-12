"""GOAT AI uvicorn factory entrypoint.

Delegates entirely to the backend package so this file stays a thin alias.

Run:
    python3 -m uvicorn server:create_app --factory --host 0.0.0.0 --port 62606 [--reload]
"""

from backend.main import create_app  # noqa: F401  (re-exported for uvicorn)

__all__ = ["create_app"]
