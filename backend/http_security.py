from __future__ import annotations

import hashlib
import logging
import time
import uuid
from typing import Callable, Protocol, cast

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response

from backend.api_errors import (
    AUTH_INVALID_API_KEY,
    AUTH_WRITE_KEY_REQUIRED,
    RATE_LIMITED,
    build_error_body,
)
from backend.config import get_settings
from backend.prometheus_metrics import record_http_request
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

access_logger = logging.getLogger("goat_ai.access")

SettingsFactory = Callable[[], Settings]


class RateLimitDecisionLike(Protocol):
    allowed: bool
    retry_after: int


class RateLimitStoreLike(Protocol):
    def get_timestamps(self, key: str, *, now: float, window_sec: int) -> list[float]:
        ...

    def replace_timestamps(self, key: str, timestamps: list[float]) -> None:
        ...


class RateLimitPolicyLike(Protocol):
    window_sec: int

    def key_for(self, subject: object) -> str:
        ...

    def decide(self, observed_timestamps: list[float], *, now: float) -> RateLimitDecisionLike:
        ...


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


def _api_key_role(settings: Settings, provided: str) -> str | None:
    """Return ``read``, ``write``, ``full``, or ``None`` if invalid."""
    if not provided:
        return None
    if settings.api_key_write:
        if provided == settings.api_key:
            return "read"
        if provided == settings.api_key_write:
            return "write"
        return None
    if settings.api_key and provided == settings.api_key:
        return "full"
    return None


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
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()


def _build_rate_limit_subject(request: Request, provided_api_key: str) -> dict[str, str]:
    return {
        "api_key_fingerprint": _fingerprint_api_key(provided_api_key),
        "method_class": _method_class(request.method),
        "owner_id": (request.headers.get(_OWNER_ID_HEADER) or "").strip(),
        "route_group": _route_template(request),
    }


def register_http_security(
    app: FastAPI,
    *,
    clock: Clock | None = None,
    rate_limit_policy_factory: Callable[[Settings], RateLimitPolicyLike],
    rate_limit_store: RateLimitStoreLike,
) -> None:
    _clock = clock if clock is not None else SystemClock()

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
            if settings.api_key:
                provided_api_key = request.headers.get(_API_KEY_HEADER, "").strip()
                role = _api_key_role(settings, provided_api_key)
                if role is None:
                    status_code = 401
                    return _build_unauthorized_response(request_id)
                if (
                    settings.api_key_write
                    and request.method not in _READ_METHODS
                    and role == "read"
                ):
                    status_code = 403
                    return _build_forbidden_write_key_response(request_id)

                rate_limit_policy = rate_limit_policy_factory(settings)
                subject = _build_rate_limit_subject(request, provided_api_key)
                rate_limit_key = rate_limit_policy.key_for(subject)
                now = _clock.monotonic()
                timestamps = rate_limit_store.get_timestamps(
                    rate_limit_key,
                    now=now,
                    window_sec=rate_limit_policy.window_sec,
                )
                decision = rate_limit_policy.decide(timestamps, now=now)
                if not decision.allowed:
                    status_code = 429
                    return _build_rate_limited_response(request_id, decision.retry_after)
                rate_limit_store.replace_timestamps(rate_limit_key, [*timestamps, now])

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
