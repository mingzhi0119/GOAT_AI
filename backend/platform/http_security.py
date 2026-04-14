from __future__ import annotations

import logging
import time
import uuid
from typing import Callable, cast

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response

from backend.api_errors import (
    AUTH_INVALID_API_KEY,
    AUTH_LOGIN_REQUIRED,
    AUTH_WRITE_KEY_REQUIRED,
    RATE_LIMITED,
    build_error_body,
)
from backend.domain.authz_types import AuthorizationContext
from backend.domain.credential_registry import (
    build_local_authorization_context,
    resolve_authorization_context,
)
from backend.domain.scope_catalog import WRITE_SCOPES
from backend.platform.config import get_settings
from backend.platform.prometheus_metrics import record_http_request
from backend.services.rate_limiter import (
    RateLimiter,
    RateLimitPolicyLike,
    StoredSlidingWindowRateLimiter,
)
from backend.services.rate_limit_store import RateLimitStore
from backend.services.browser_access_session import (
    build_shared_access_authorization_context,
    read_shared_access_session_from_request,
)
from backend.services.account_auth import (
    build_account_authorization_context,
    read_account_session_from_request,
)
from goat_ai.shared.clocks import Clock, SystemClock
from goat_ai.config.settings import Settings
from goat_ai.telemetry.request_context import reset_request_id, set_request_id

_HEALTH_PATH = "/api/health"
_READY_PATH = "/api/ready"
_AUTH_SESSION_PATH = "/api/auth/session"
_AUTH_LOGIN_PATH = "/api/auth/login"
_AUTH_LOGOUT_PATH = "/api/auth/logout"
_ACCOUNT_LOGIN_PATH = "/api/auth/account/login"
_GOOGLE_LOGIN_PATH = "/api/auth/account/google"
_GOOGLE_LOGIN_URL_PATH = "/api/auth/account/google/url"
_API_KEY_HEADER = "X-GOAT-API-Key"
_OWNER_ID_HEADER = "X-GOAT-Owner-Id"
_REQUEST_ID_HEADER = "X-Request-ID"
_RETRY_AFTER_HEADER = "Retry-After"
_CACHE_CONTROL_HEADER = "Cache-Control"
_VARY_HEADER = "Vary"
_RATE_LIMIT_MESSAGE = "Too many requests. Please try again shortly."
_UNAUTHORIZED_MESSAGE = "Invalid or missing API key."
_LOGIN_REQUIRED_MESSAGE = "Browser login required."
_READ_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
_WRITE_KEY_DETAIL = "Write operations require the write API key."
_SENSITIVE_VARY_HEADERS = (
    "Cookie",
    _API_KEY_HEADER,
    _OWNER_ID_HEADER,
)
access_logger = logging.getLogger("goat_ai.access")

SettingsFactory = Callable[[], Settings]


def _resolve_settings(app: FastAPI) -> Settings:
    override = app.dependency_overrides.get(get_settings)
    if override is None:
        return get_settings()
    settings_factory = cast(SettingsFactory, override)
    return settings_factory()


def _is_public_path(path: str) -> bool:
    return path in {
        _HEALTH_PATH,
        _READY_PATH,
        _AUTH_SESSION_PATH,
        _AUTH_LOGIN_PATH,
        _AUTH_LOGOUT_PATH,
        _ACCOUNT_LOGIN_PATH,
        _GOOGLE_LOGIN_PATH,
        _GOOGLE_LOGIN_URL_PATH,
    }


def _route_template(request: Request) -> str:
    route = request.scope.get("route")
    path_attr = getattr(route, "path", None) if route is not None else None
    if isinstance(path_attr, str) and path_attr:
        return path_attr
    return request.url.path.split("?")[0]


def _build_forbidden_write_key_response(request_id: str) -> JSONResponse:
    response = JSONResponse(
        status_code=403,
        content=build_error_body(
            detail=_WRITE_KEY_DETAIL,
            code=AUTH_WRITE_KEY_REQUIRED,
            status_code=403,
        ),
    )
    response.headers[_REQUEST_ID_HEADER] = request_id
    return response


def _build_unauthorized_response(request_id: str) -> JSONResponse:
    response = JSONResponse(
        status_code=401,
        content=build_error_body(
            detail=_UNAUTHORIZED_MESSAGE,
            code=AUTH_INVALID_API_KEY,
            status_code=401,
        ),
    )
    response.headers[_REQUEST_ID_HEADER] = request_id
    return response


def _build_login_required_response(request_id: str) -> JSONResponse:
    response = JSONResponse(
        status_code=401,
        content=build_error_body(
            detail=_LOGIN_REQUIRED_MESSAGE,
            code=AUTH_LOGIN_REQUIRED,
            status_code=401,
        ),
    )
    response.headers[_REQUEST_ID_HEADER] = request_id
    return response


def _build_rate_limited_response(request_id: str, retry_after: int) -> JSONResponse:
    response = JSONResponse(
        status_code=429,
        content=build_error_body(
            detail=_RATE_LIMIT_MESSAGE,
            code=RATE_LIMITED,
            status_code=429,
        ),
    )
    response.headers[_REQUEST_ID_HEADER] = request_id
    response.headers[_RETRY_AFTER_HEADER] = str(retry_after)
    return response


def _method_class(method: str) -> str:
    return "read" if method in _READ_METHODS else "write"


def _fingerprint_api_key(api_key: str) -> str:
    import hashlib

    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()


def _has_any_write_scope(scopes: object) -> bool:
    if not isinstance(scopes, frozenset):
        return False
    return bool(WRITE_SCOPES & scopes)


def _build_rate_limit_subject(
    request: Request,
    *,
    auth_context: AuthorizationContext,
    provided_api_key: str = "",
) -> dict[str, str]:
    subject = {
        "method_class": _method_class(request.method),
        "owner_id": auth_context.legacy_owner_id,
        "route_group": _route_template(request),
    }
    if provided_api_key:
        subject["api_key_fingerprint"] = _fingerprint_api_key(provided_api_key)
    else:
        subject["principal_id"] = auth_context.principal_id.value
    return subject


def _append_vary_headers(response: Response, *headers: str) -> None:
    existing = {
        item.strip()
        for item in response.headers.get(_VARY_HEADER, "").split(",")
        if item.strip()
    }
    existing.update(headers)
    response.headers[_VARY_HEADER] = ", ".join(sorted(existing))


def _apply_sensitive_cache_headers(request: Request, response: Response) -> None:
    if not request.url.path.startswith("/api/"):
        return
    if request.url.path in {_HEALTH_PATH, _READY_PATH}:
        return
    if request.method not in _READ_METHODS and not request.url.path.startswith(
        "/api/artifacts/"
    ):
        return
    response.headers.setdefault(_CACHE_CONTROL_HEADER, "no-store")
    _append_vary_headers(response, *_SENSITIVE_VARY_HEADERS)


def _default_rate_limiter_factory(
    *,
    rate_limit_policy_factory: Callable[[Settings], RateLimitPolicyLike],
    rate_limit_store: RateLimitStore,
) -> Callable[[Settings], RateLimiter]:
    def factory(settings: Settings) -> RateLimiter:
        return StoredSlidingWindowRateLimiter(
            policy=rate_limit_policy_factory(settings),
            store=rate_limit_store,
        )

    return factory


def register_http_security(
    app: FastAPI,
    *,
    clock: Clock | None = None,
    rate_limiter_factory: Callable[[Settings], RateLimiter] | None = None,
    rate_limit_policy_factory: Callable[[Settings], RateLimitPolicyLike] | None = None,
    rate_limit_store: RateLimitStore | None = None,
) -> None:
    _clock = clock if clock is not None else SystemClock()
    if rate_limiter_factory is None:
        if rate_limit_policy_factory is None or rate_limit_store is None:
            raise ValueError(
                "register_http_security requires either rate_limiter_factory or "
                "both rate_limit_policy_factory and rate_limit_store."
            )
        rate_limiter_factory = _default_rate_limiter_factory(
            rate_limit_policy_factory=rate_limit_policy_factory,
            rate_limit_store=rate_limit_store,
        )

    @app.middleware("http")
    async def security_middleware(
        request: Request, call_next: Callable[[Request], Response]
    ) -> Response:
        inbound = request.headers.get(_REQUEST_ID_HEADER, "").strip()
        request_id = inbound if inbound else str(uuid.uuid4())
        token = set_request_id(request_id)
        start = time.perf_counter()
        route_key = _route_template(request)
        status_code = 500
        try:
            settings = _resolve_settings(app)
            request.state.request_id = request_id
            shared_session = read_shared_access_session_from_request(
                request,
                settings=settings,
            )
            if shared_session is not None:
                request.state.shared_access_session = shared_session
                request.state.authorization_context = (
                    build_shared_access_authorization_context(shared_session)
                )
            else:
                account_session = read_account_session_from_request(
                    request,
                    settings=settings,
                )
                if account_session is not None:
                    request.state.account_session = account_session
                    request.state.authorization_context = (
                        build_account_authorization_context(account_session)
                    )

            if _is_public_path(request.url.path):
                response = await call_next(request)
                status_code = response.status_code
                response.headers[_REQUEST_ID_HEADER] = request_id
                _apply_sensitive_cache_headers(request, response)
                return response

            auth_context = getattr(request.state, "authorization_context", None)
            if isinstance(auth_context, AuthorizationContext):
                subject = _build_rate_limit_subject(
                    request,
                    auth_context=auth_context,
                )
                now = _clock.monotonic()
                rate_limiter = rate_limiter_factory(settings)
                decision = rate_limiter.evaluate(subject=subject, now=now)
                if not decision.allowed:
                    status_code = 429
                    response = _build_rate_limited_response(
                        request_id, decision.retry_after
                    )
                    _apply_sensitive_cache_headers(request, response)
                    return response
            elif settings.api_key:
                provided_api_key = request.headers.get(_API_KEY_HEADER, "").strip()
                if not provided_api_key and settings.browser_auth_required:
                    status_code = 401
                    response = _build_login_required_response(request_id)
                    _apply_sensitive_cache_headers(request, response)
                    return response
                legacy_owner_id = (request.headers.get(_OWNER_ID_HEADER) or "").strip()
                auth_context = resolve_authorization_context(
                    provided_api_key=provided_api_key,
                    settings=settings,
                    legacy_owner_id=legacy_owner_id,
                )
                if auth_context is None:
                    status_code = 401
                    response = _build_unauthorized_response(request_id)
                    _apply_sensitive_cache_headers(request, response)
                    return response
                if (
                    settings.api_key_write
                    and request.method not in _READ_METHODS
                    and not _has_any_write_scope(auth_context.scopes)
                ):
                    status_code = 403
                    response = _build_forbidden_write_key_response(request_id)
                    _apply_sensitive_cache_headers(request, response)
                    return response
                request.state.authorization_context = auth_context

                subject = _build_rate_limit_subject(
                    request,
                    auth_context=auth_context,
                    provided_api_key=provided_api_key,
                )
                now = _clock.monotonic()
                rate_limiter = rate_limiter_factory(settings)
                decision = rate_limiter.evaluate(subject=subject, now=now)
                if not decision.allowed:
                    status_code = 429
                    response = _build_rate_limited_response(
                        request_id, decision.retry_after
                    )
                    _apply_sensitive_cache_headers(request, response)
                    return response
            elif settings.browser_auth_required:
                status_code = 401
                response = _build_login_required_response(request_id)
                _apply_sensitive_cache_headers(request, response)
                return response
            else:
                request.state.authorization_context = build_local_authorization_context(
                    legacy_owner_id=(
                        request.headers.get(_OWNER_ID_HEADER) or ""
                    ).strip()
                )

            response = await call_next(request)
            status_code = response.status_code
            response.headers[_REQUEST_ID_HEADER] = request_id
            _apply_sensitive_cache_headers(request, response)
            return response
        except BaseException:
            status_code = 500
            raise
        finally:
            duration_sec = time.perf_counter() - start
            record_http_request(
                method=request.method,
                route=route_key,
                status_code=status_code,
                duration_sec=duration_sec,
            )
            access_logger.info(
                "http_request",
                extra={
                    "route": route_key,
                    "status": status_code,
                    "duration_ms": round(duration_sec * 1000, 3),
                },
            )
            reset_request_id(token)
