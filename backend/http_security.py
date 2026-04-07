from __future__ import annotations

import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from typing import Callable, cast

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response

from backend.config import get_settings
from goat_ai.config import Settings

_HEALTH_PATH = "/api/health"
_API_KEY_HEADER = "X-GOAT-API-Key"
_REQUEST_ID_HEADER = "X-Request-ID"
_RETRY_AFTER_HEADER = "Retry-After"
_RATE_LIMIT_MESSAGE = "Too many requests. Please try again shortly."
_UNAUTHORIZED_MESSAGE = "Invalid or missing API key."

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
    return path == _HEALTH_PATH


def _build_unauthorized_response(request_id: str) -> JSONResponse:
    response = JSONResponse(status_code=401, content={"detail": _UNAUTHORIZED_MESSAGE})
    response.headers[_REQUEST_ID_HEADER] = request_id
    return response


def _build_rate_limited_response(request_id: str, retry_after: int) -> JSONResponse:
    response = JSONResponse(status_code=429, content={"detail": _RATE_LIMIT_MESSAGE})
    response.headers[_REQUEST_ID_HEADER] = request_id
    response.headers[_RETRY_AFTER_HEADER] = str(retry_after)
    return response


def register_http_security(app: FastAPI) -> None:
    limiter = InMemoryRateLimiter()

    @app.middleware("http")
    async def security_middleware(request: Request, call_next: Callable[[Request], Response]) -> Response:
        request_id = str(uuid.uuid4())
        if _is_public_path(request.url.path):
            response = await call_next(request)
            response.headers[_REQUEST_ID_HEADER] = request_id
            return response

        settings = _resolve_settings(app)
        if settings.api_key:
            provided_api_key = request.headers.get(_API_KEY_HEADER, "").strip()
            if provided_api_key != settings.api_key:
                return _build_unauthorized_response(request_id)

            allowed, retry_after = limiter.allow(
                provided_api_key,
                now=time.monotonic(),
                window_sec=settings.rate_limit_window_sec,
                max_requests=settings.rate_limit_max_requests,
            )
            if not allowed:
                return _build_rate_limited_response(request_id, retry_after)

        response = await call_next(request)
        response.headers[_REQUEST_ID_HEADER] = request_id
        return response
