"""Placeholder routes for future model code execution (§15 gate enforcement)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from backend.application.code_sandbox import ensure_code_sandbox_enabled
from backend.domain.authz_types import AuthorizationContext
from backend.application.ports import Settings
from backend.config import get_settings
from backend.dependencies import get_authorization_context
from backend.models.common import ErrorResponse

router = APIRouter()


@router.post(
    "/code-sandbox/exec",
    summary="Execute code in sandbox (not implemented)",
    responses={
        401: {"model": ErrorResponse},
        403: {
            "model": ErrorResponse,
            "description": "Policy denied (FEATURE_DISABLED)",
        },
        429: {"model": ErrorResponse},
        503: {
            "model": ErrorResponse,
            "description": "Runtime gate closed (FEATURE_UNAVAILABLE)",
        },
        501: {"description": "Execution engine not implemented"},
    },
)
def post_code_sandbox_exec(
    settings: Settings = Depends(get_settings),
    auth_context: AuthorizationContext = Depends(get_authorization_context),
) -> dict[str, str]:
    """Scaffold: enforces the feature gate; returns 501 when the gate passes and execution is not built yet."""
    ensure_code_sandbox_enabled(settings, auth_context)
    raise HTTPException(
        status_code=501, detail="Code sandbox execution is not implemented yet."
    )
