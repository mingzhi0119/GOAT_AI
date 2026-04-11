from __future__ import annotations

import logging
import time
import uuid
from typing import Callable, cast

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response

from backend.api_errors import (
    AUTH_INVALID_API_KEY,
    AUTH_WRITE_KEY_REQUIRED,
    RATE_LIMITED,
    build_error_body,
)
from backend.domain.credential_registry import (
    build_local_authorization_context,
    resolve_authorization_context,
)
from backend.config import get_settings
from backend.prometheus_metrics import record_http_request
from backend.services.rate_limiter import (
    RateLimiter,
    RateLimitPolicyLike,
    StoredSlidingWindowRateLimiter,
)
from backend.services.rate_limit_store import RateLimitStore
from goat_ai.clocks import Clock, SystemClock
from goat_ai.config import Settings
from goat_ai.request_context import reset_request_id, set_request_id

_HEALTH_PATH = "/api/health"
_READY_PATH = "/api/ready"
_API_KEY_HEADER = "X-GOAT-API-Key"
_OWNER_ID_HEADER = "X-GOAT-Owner-Id"
_REQUEST_ID_HEADER = "X-Request-ID"
_RETRY_AFTER_HEADER = "Retry-After"
_RATE_LIMIT_MESSAGE = "Too many requests. Please try again shortly."
_UNAUTHORIZED_MESSAGE = "Invalid or missing API key."
_READ_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
_WRITE_KEY_DETAIL = "Write operations require the write API key."
_WRITE_SCOPES = frozenset(
    {
        "chat:write",
        "history:write",
        "knowledge:write",
        "media:write",
        "artifact:write",
        "sandbox:execute",
    }
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
    return path in {_HEALTH_PATH, _READY_PATH}


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
    return bool(_WRITE_SCOPES & scopes)


def _build_rate_limit_subject(
    request: Request, provided_api_key: str
) -> dict[str, str]:
    return {
        "api_key_fingerprint": _fingerprint_api_key(provided_api_key),
        "method_class": _method_class(request.method),
        "owner_id": (request.headers.get(_OWNER_ID_HEADER) or "").strip(),
        "route_group": _route_template(request),
    }


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
            if _is_public_path(request.url.path):
                response = await call_next(request)
                status_code = response.status_code
                response.headers[_REQUEST_ID_HEADER] = request_id
                return response

            settings = _resolve_settings(app)
            request.state.request_id = request_id
            if settings.api_key:
                provided_api_key = request.headers.get(_API_KEY_HEADER, "").strip()
                legacy_owner_id = (request.headers.get(_OWNER_ID_HEADER) or "").strip()
                auth_context = resolve_authorization_context(
                    provided_api_key=provided_api_key,
                    settings=settings,
                    legacy_owner_id=legacy_owner_id,
                )
                if auth_context is None:
                    status_code = 401
                    return _build_unauthorized_response(request_id)
                if (
                    settings.api_key_write
                    and request.method not in _READ_METHODS
                    and not _has_any_write_scope(auth_context.scopes)
                ):
                    status_code = 403
                    return _build_forbidden_write_key_response(request_id)
                request.state.authorization_context = auth_context

                subject = _build_rate_limit_subject(request, provided_api_key)
                now = _clock.monotonic()
                rate_limiter = rate_limiter_factory(settings)
                decision = rate_limiter.evaluate(subject=subject, now=now)
                if not decision.allowed:
                    status_code = 429
                    return _build_rate_limited_response(
                        request_id, decision.retry_after
                    )
            else:
                request.state.authorization_context = (
                    build_local_authorization_context()
                )

            response = await call_next(request)
            status_code = response.status_code
            response.headers[_REQUEST_ID_HEADER] = request_id
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
