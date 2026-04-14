"""Browser authentication router for shared-password and account login."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse

from backend.api_errors import (
    AUTH_INVALID_ACCESS_PASSWORD,
    AUTH_INVALID_ACCOUNT_CREDENTIALS,
    AUTH_INVALID_GOOGLE_STATE,
    AUTH_INVALID_GOOGLE_TOKEN,
    BAD_REQUEST,
    RATE_LIMITED,
    build_error_body,
)
from backend.application.ports import Settings
from backend.models.auth import (
    AccountLoginRequest,
    AuthenticatedBrowserUser,
    BrowserAuthSessionResponse,
    BrowserLoginMethod,
    GoogleOAuthLoginRequest,
    GoogleOAuthUrlResponse,
    SharedAccessLoginRequest,
)
from backend.models.common import ErrorResponse
from backend.platform.config import get_settings
from backend.platform.dependencies import get_account_repository
from backend.services.account_auth import (
    AccountSession,
    account_auth_enabled,
    authenticate_local_account,
    clear_account_session_cookie,
    evaluate_account_login_attempt,
    issue_account_session,
    resolve_google_account,
    set_account_session_cookie,
)
from backend.services.account_repository import AccountRepository
from backend.services.browser_access_session import (
    SharedAccessSession,
    clear_shared_access_cookie,
    evaluate_shared_access_login_attempt,
    issue_shared_access_session,
    set_shared_access_cookie,
    shared_access_enabled,
    verify_shared_access_password,
)
from backend.services.google_oauth_service import (
    InvalidGoogleStateError,
    InvalidGoogleTokenError,
    build_google_oauth_authorization_url,
    clear_google_oauth_state_cookie,
    exchange_google_code_for_identity,
    google_oauth_enabled,
    issue_google_oauth_state,
    set_google_oauth_state_cookie,
    validate_google_oauth_state,
)

router = APIRouter()

_SHARED_LOGIN_DISABLED_DETAIL = (
    "Shared browser access is not enabled on this deployment."
)
_ACCOUNT_LOGIN_DISABLED_DETAIL = "Account login is not enabled on this deployment."
_GOOGLE_LOGIN_DISABLED_DETAIL = "Google login is not enabled on this deployment."
_INVALID_PASSWORD_DETAIL = "Invalid shared access password."
_INVALID_ACCOUNT_CREDENTIALS_DETAIL = "Invalid email or password."
_INVALID_GOOGLE_TOKEN_DETAIL = "Google login failed. Please try again."
_INVALID_GOOGLE_STATE_DETAIL = "Google login session expired. Please try again."
_LOGIN_RATE_LIMIT_DETAIL = "Too many login attempts. Please try again shortly."


def _available_login_methods(settings: Settings) -> list[BrowserLoginMethod]:
    methods: list[BrowserLoginMethod] = []
    if shared_access_enabled(settings):
        methods.append("shared_password")
    if account_auth_enabled(settings):
        methods.append("account_password")
    if google_oauth_enabled(settings):
        methods.append("google")
    return methods


def _account_user(session: AccountSession | None) -> AuthenticatedBrowserUser | None:
    if session is None:
        return None
    return AuthenticatedBrowserUser(
        id=session.user_id,
        email=session.email,
        display_name=session.display_name,
        provider=session.provider,
    )


def _active_login_method(
    *,
    shared_session: SharedAccessSession | None,
    account_session: AccountSession | None,
) -> BrowserLoginMethod | None:
    if shared_session is not None:
        return "shared_password"
    if account_session is None:
        return None
    return "google" if account_session.provider == "google" else "account_password"


def _session_status_payload(
    *,
    settings: Settings,
    shared_session: SharedAccessSession | None,
    account_session: AccountSession | None,
) -> BrowserAuthSessionResponse:
    auth_required = settings.browser_auth_required
    active_login_method = _active_login_method(
        shared_session=shared_session,
        account_session=account_session,
    )
    expires_at: str | None = None
    if shared_session is not None:
        expires_at = shared_session.expires_at
    elif account_session is not None:
        expires_at = account_session.expires_at
    return BrowserAuthSessionResponse(
        auth_required=auth_required,
        authenticated=(shared_session is not None or account_session is not None),
        expires_at=expires_at,
        available_login_methods=_available_login_methods(settings),
        active_login_method=active_login_method,
        user=_account_user(account_session),
    )


def _current_shared_access_session(request: Request) -> SharedAccessSession | None:
    session = getattr(request.state, "shared_access_session", None)
    return session if isinstance(session, SharedAccessSession) else None


def _current_account_session(request: Request) -> AccountSession | None:
    session = getattr(request.state, "account_session", None)
    return session if isinstance(session, AccountSession) else None


@router.get(
    "/auth/session",
    response_model=BrowserAuthSessionResponse,
    summary="Read browser authentication session state",
    responses={
        429: {"model": ErrorResponse},
    },
)
def get_shared_access_session(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> BrowserAuthSessionResponse:
    return _session_status_payload(
        settings=settings,
        shared_session=_current_shared_access_session(request),
        account_session=_current_account_session(request),
    )


@router.post(
    "/auth/login",
    response_model=BrowserAuthSessionResponse,
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
                detail=_SHARED_LOGIN_DISABLED_DETAIL,
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
    if not verify_shared_access_password(settings, password=payload.password):
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
            shared_session=session,
            account_session=None,
        ).model_dump(),
    )
    clear_account_session_cookie(response)
    clear_google_oauth_state_cookie(response)
    set_shared_access_cookie(response, session=session, settings=settings)
    return response


@router.post(
    "/auth/account/login",
    response_model=BrowserAuthSessionResponse,
    summary="Create a browser account session",
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
    },
)
def login_account(
    payload: AccountLoginRequest,
    request: Request,
    settings: Settings = Depends(get_settings),
    repository: AccountRepository = Depends(get_account_repository),
) -> JSONResponse:
    if not account_auth_enabled(settings):
        raise HTTPException(
            status_code=400,
            detail=build_error_body(
                detail=_ACCOUNT_LOGIN_DISABLED_DETAIL,
                code=BAD_REQUEST,
                status_code=400,
            ),
        )
    decision = evaluate_account_login_attempt(
        request,
        route_group="/api/auth/account/login",
        email=payload.email,
    )
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
    user = authenticate_local_account(
        repository,
        email=payload.email,
        password=payload.password,
    )
    if user is None:
        raise HTTPException(
            status_code=401,
            detail=build_error_body(
                detail=_INVALID_ACCOUNT_CREDENTIALS_DETAIL,
                code=AUTH_INVALID_ACCOUNT_CREDENTIALS,
                status_code=401,
            ),
        )
    session = issue_account_session(
        user=user,
        provider="local",
        settings=settings,
    )
    response = JSONResponse(
        status_code=200,
        content=_session_status_payload(
            settings=settings,
            shared_session=None,
            account_session=session,
        ).model_dump(),
    )
    clear_shared_access_cookie(response)
    clear_google_oauth_state_cookie(response)
    set_account_session_cookie(response, session=session, settings=settings)
    return response


@router.get(
    "/auth/account/google/url",
    response_model=GoogleOAuthUrlResponse,
    summary="Create a Google OAuth authorization URL",
    responses={
        400: {"model": ErrorResponse},
    },
)
def get_google_login_url(
    settings: Settings = Depends(get_settings),
) -> JSONResponse:
    if not google_oauth_enabled(settings):
        raise HTTPException(
            status_code=400,
            detail=build_error_body(
                detail=_GOOGLE_LOGIN_DISABLED_DETAIL,
                code=BAD_REQUEST,
                status_code=400,
            ),
        )
    oauth_state = issue_google_oauth_state(settings)
    response = JSONResponse(
        status_code=200,
        content=GoogleOAuthUrlResponse(
            authorization_url=build_google_oauth_authorization_url(
                settings,
                state=oauth_state.state,
            ),
            state_expires_at=oauth_state.expires_at,
        ).model_dump(),
    )
    set_google_oauth_state_cookie(
        response,
        oauth_state=oauth_state,
        settings=settings,
    )
    return response


@router.post(
    "/auth/account/google",
    response_model=BrowserAuthSessionResponse,
    summary="Create a browser account session from Google OAuth",
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
    },
)
def login_google_account(
    payload: GoogleOAuthLoginRequest,
    request: Request,
    settings: Settings = Depends(get_settings),
    repository: AccountRepository = Depends(get_account_repository),
) -> JSONResponse:
    if not google_oauth_enabled(settings):
        raise HTTPException(
            status_code=400,
            detail=build_error_body(
                detail=_GOOGLE_LOGIN_DISABLED_DETAIL,
                code=BAD_REQUEST,
                status_code=400,
            ),
        )
    decision = evaluate_account_login_attempt(
        request,
        route_group="/api/auth/account/google",
    )
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
    try:
        validate_google_oauth_state(
            cookie_value=(request.cookies.get("goat_google_oauth_state") or "").strip(),
            state=payload.state,
            settings=settings,
        )
    except InvalidGoogleStateError as exc:
        raise HTTPException(
            status_code=401,
            detail=build_error_body(
                detail=_INVALID_GOOGLE_STATE_DETAIL,
                code=AUTH_INVALID_GOOGLE_STATE,
                status_code=401,
            ),
        ) from exc
    try:
        identity = exchange_google_code_for_identity(settings, code=payload.code)
    except InvalidGoogleTokenError as exc:
        raise HTTPException(
            status_code=401,
            detail=build_error_body(
                detail=_INVALID_GOOGLE_TOKEN_DETAIL,
                code=AUTH_INVALID_GOOGLE_TOKEN,
                status_code=401,
            ),
        ) from exc
    user = resolve_google_account(
        repository,
        provider_subject=identity.subject,
        email=identity.email,
        display_name=identity.display_name,
    )
    session = issue_account_session(
        user=user,
        provider="google",
        settings=settings,
    )
    response = JSONResponse(
        status_code=200,
        content=_session_status_payload(
            settings=settings,
            shared_session=None,
            account_session=session,
        ).model_dump(),
    )
    clear_shared_access_cookie(response)
    clear_google_oauth_state_cookie(response)
    set_account_session_cookie(response, session=session, settings=settings)
    return response


@router.post(
    "/auth/logout",
    status_code=204,
    summary="Clear the current browser authentication session",
)
def logout_shared_access() -> Response:
    response = Response(status_code=204)
    clear_shared_access_cookie(response)
    clear_account_session_cookie(response)
    clear_google_oauth_state_cookie(response)
    return response
