"""Shared browser-access authentication router."""

from __future__ import annotations

import hmac

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse

from backend.api_errors import (
    AUTH_INVALID_ACCESS_PASSWORD,
    BAD_REQUEST,
    RATE_LIMITED,
    build_error_body,
)
from backend.models.auth import SharedAccessLoginRequest, SharedAccessSessionResponse
from backend.models.common import ErrorResponse
from backend.platform.config import get_settings
from backend.services.browser_access_session import (
    SharedAccessSession,
    clear_shared_access_cookie,
    evaluate_shared_access_login_attempt,
    issue_shared_access_session,
    set_shared_access_cookie,
    shared_access_enabled,
)
from goat_ai.config.settings import Settings

router = APIRouter()

_LOGIN_DISABLED_DETAIL = "Shared browser access is not enabled on this deployment."
_INVALID_PASSWORD_DETAIL = "Invalid shared access password."
_LOGIN_RATE_LIMIT_DETAIL = "Too many login attempts. Please try again shortly."


def _session_status_payload(
    *,
    settings: Settings,
    session: SharedAccessSession | None,
) -> SharedAccessSessionResponse:
    if not shared_access_enabled(settings):
        return SharedAccessSessionResponse(
            auth_required=False,
            authenticated=False,
            expires_at=None,
        )
    return SharedAccessSessionResponse(
        auth_required=True,
        authenticated=session is not None,
        expires_at=session.expires_at if session is not None else None,
    )


def _current_shared_access_session(request: Request) -> SharedAccessSession | None:
    session = getattr(request.state, "shared_access_session", None)
    return session if isinstance(session, SharedAccessSession) else None


@router.get(
    "/auth/session",
    response_model=SharedAccessSessionResponse,
    summary="Read browser shared-access session state",
    responses={
        429: {"model": ErrorResponse},
    },
)
def get_shared_access_session(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> SharedAccessSessionResponse:
    return _session_status_payload(
        settings=settings,
        session=_current_shared_access_session(request),
    )


@router.post(
    "/auth/login",
    response_model=SharedAccessSessionResponse,
    summary="Create a browser shared-access session",
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
    },
)
def login_shared_access(
    payload: SharedAccessLoginRequest,
    request: Request,
    settings: Settings = Depends(get_settings),
) -> JSONResponse:
    if not shared_access_enabled(settings):
        raise HTTPException(
            status_code=400,
            detail=build_error_body(
                detail=_LOGIN_DISABLED_DETAIL,
                code=BAD_REQUEST,
                status_code=400,
            ),
        )
    decision = evaluate_shared_access_login_attempt(request)
    if not decision.allowed:
        raise HTTPException(
            status_code=429,
            detail=build_error_body(
                detail=_LOGIN_RATE_LIMIT_DETAIL,
                code=RATE_LIMITED,
                status_code=429,
            ),
            headers={"Retry-After": str(decision.retry_after)},
        )
    if not hmac.compare_digest(
        payload.password.strip(),
        settings.shared_access_password.strip(),
    ):
        raise HTTPException(
            status_code=401,
            detail=build_error_body(
                detail=_INVALID_PASSWORD_DETAIL,
                code=AUTH_INVALID_ACCESS_PASSWORD,
                status_code=401,
            ),
        )
    session = issue_shared_access_session(settings)
    response = JSONResponse(
        status_code=200,
        content=_session_status_payload(
            settings=settings,
            session=session,
        ).model_dump(),
    )
    set_shared_access_cookie(response, session=session, settings=settings)
    return response


@router.post(
    "/auth/logout",
    status_code=204,
    summary="Clear the browser shared-access session",
)
def logout_shared_access() -> Response:
    response = Response(status_code=204)
    clear_shared_access_cookie(response)
    return response
