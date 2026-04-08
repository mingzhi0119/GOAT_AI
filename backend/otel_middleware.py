"""ASGI middleware — propagates W3C ``traceparent`` when OpenTelemetry is enabled."""
from __future__ import annotations

from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from goat_ai.otel_tracing import attach_request_trace_context, is_otel_enabled


class OtelTraceContextMiddleware(BaseHTTPMiddleware):
    """Extracts trace context from request headers for downstream spans (e.g. Ollama HTTP)."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if not is_otel_enabled():
            return await call_next(request)
        with attach_request_trace_context(request.headers):
            return await call_next(request)
