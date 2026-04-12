"""Stable API error codes, request correlation context, and JSON error bodies.

Phase 13 §13.0 — single module to satisfy import-layer rules (no sibling cross-imports).
See ``docs/api/API_ERRORS.md`` for the registry.
"""

from __future__ import annotations

from typing import Any, Final

from goat_ai.telemetry.request_context import get_request_id

# ── Stable error codes (do not rename once shipped) ──────────────────────────
INTERNAL_ERROR: Final = "INTERNAL_ERROR"
INFERENCE_BACKEND_UNAVAILABLE: Final = "INFERENCE_BACKEND_UNAVAILABLE"
AUTH_INVALID_API_KEY: Final = "AUTH_INVALID_API_KEY"
AUTH_WRITE_KEY_REQUIRED: Final = "AUTH_WRITE_KEY_REQUIRED"
AUTH_SESSION_OWNER_REQUIRED: Final = "AUTH_SESSION_OWNER_REQUIRED"
RATE_LIMITED: Final = "RATE_LIMITED"
NOT_FOUND: Final = "NOT_FOUND"
BAD_REQUEST: Final = "BAD_REQUEST"
RESOURCE_CONFLICT: Final = "RESOURCE_CONFLICT"
REQUEST_VALIDATION_ERROR: Final = "REQUEST_VALIDATION_ERROR"
IDEMPOTENCY_CONFLICT: Final = "IDEMPOTENCY_CONFLICT"
NOT_IMPLEMENTED: Final = "NOT_IMPLEMENTED"
KNOWLEDGE_NOT_FOUND: Final = "KNOWLEDGE_NOT_FOUND"
MEDIA_NOT_FOUND: Final = "MEDIA_NOT_FOUND"
ARTIFACT_NOT_FOUND: Final = "ARTIFACT_NOT_FOUND"
VISION_NOT_SUPPORTED: Final = "VISION_NOT_SUPPORTED"
FEATURE_DISABLED: Final = "FEATURE_DISABLED"
FEATURE_UNAVAILABLE: Final = "FEATURE_UNAVAILABLE"

_DEFAULT_CODE_BY_STATUS: dict[int, str] = {
    400: BAD_REQUEST,
    401: AUTH_INVALID_API_KEY,
    403: FEATURE_DISABLED,
    404: NOT_FOUND,
    409: IDEMPOTENCY_CONFLICT,
    422: REQUEST_VALIDATION_ERROR,
    429: RATE_LIMITED,
    500: INTERNAL_ERROR,
    501: NOT_IMPLEMENTED,
    503: INFERENCE_BACKEND_UNAVAILABLE,
}

# Documented for Wave B client retry policy (not enforced here).
RETRYABLE_CODES: frozenset[str] = frozenset(
    {INFERENCE_BACKEND_UNAVAILABLE, FEATURE_UNAVAILABLE, RATE_LIMITED}
)


def default_code_for_http_status(status_code: int) -> str:
    """Return the canonical error code for an HTTP status, or INTERNAL_ERROR."""
    return _DEFAULT_CODE_BY_STATUS.get(status_code, INTERNAL_ERROR)


def build_error_body(
    *,
    detail: str | list[Any] | dict[str, Any],
    code: str | None = None,
    status_code: int | None = None,
) -> dict[str, Any]:
    """Build ``{"detail", "code", "request_id"?}`` for JSON responses."""
    resolved = (
        code
        if code is not None
        else (
            default_code_for_http_status(status_code)
            if status_code is not None
        else default_code_for_http_status(500)
    )
    )
    body: dict[str, Any] = {"detail": detail, "code": resolved}
    rid = get_request_id()
    if rid:
        body["request_id"] = rid
    return body
