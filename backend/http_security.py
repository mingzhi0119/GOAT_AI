from __future__ import annotations

import logging
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from typing import Callable, cast

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response

from backend.api_errors import (
    AUTH_INVALID_API_KEY,
    RATE_LIMITED,
    build_error_body,
)
from backend.config import get_settings
from backend.prometheus_metrics import record_http_request
from goat_ai.config import Settings
from goat_ai.request_context import reset_request_id, set_request_id

_HEALTH_PATH = "/api/health"
_READY_PATH = "/api/ready"
_API_KEY_HEADER = "X-GOAT-API-Key"
_REQUEST_ID_HEADER = "X-Request-ID"
_RETRY_AFTER_HEADER = "Retry-After"
_RATE_LIMIT_MESSAGE = "Too many requests. Please try again shortly."
_UNAUTHORIZED_MESSAGE = "Invalid or missing API key."

access_logger = logging.getLogger("goat_ai.access")

SettingsFactory = Callable[[], Settings]


@dataclass
class InMemoryRateLimiter:
    _requests_by_key: dict[str, deque[float]] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def allow(self, key: str, *, now: float, window_sec: int, max_requests: int) -> tuple[bool, int]:
        with self._lock:
            bucket = self._requests_by_key.setdefault(key, deque())
            cutoff = now - float(window_sec)
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()

            if len(bucket) >= max_requests:
                retry_after = max(1, int(bucket[0] + float(window_sec) - now))
                return False, retry_after

            bucket.append(now)
            return True, 0


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


def register_http_security(app: FastAPI) -> None:
    limiter = InMemoryRateLimiter()

    @app.middleware("http")
    async def security_middleware(request: Request, call_next: Callable[[Request], Response]) -> Response:
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
                if provided_api_key != settings.api_key:
                    status_code = 401
                    return _build_unauthorized_response(request_id)

                allowed, retry_after = limiter.allow(
                    provided_api_key,
                    now=time.monotonic(),
                    window_sec=settings.rate_limit_window_sec,
                    max_requests=settings.rate_limit_max_requests,
                )
                if not allowed:
                    status_code = 429
                    return _build_rate_limited_response(request_id, retry_after)

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
