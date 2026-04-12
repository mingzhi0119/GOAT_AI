"""Lazy OpenTelemetry wiring — only imports SDK/exporters when GOAT_OTEL_ENABLED is set."""

from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from typing import Any, Generator, Iterator, Mapping

logger = logging.getLogger(__name__)
_provider_initialized = False


def is_otel_enabled() -> bool:
    return os.environ.get("GOAT_OTEL_ENABLED", "0").lower() in ("1", "true", "yes")


def init_otel_if_enabled() -> None:
    """Idempotent: configures TracerProvider + exporter when enabled. No-op when disabled."""
    global _provider_initialized
    if _provider_initialized or not is_otel_enabled():
        return
    from opentelemetry import trace
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

    provider = TracerProvider(resource=Resource.create({"service.name": "goat-ai"}))
    exporter_kind = os.environ.get("GOAT_OTEL_EXPORTER", "console").strip().lower()
    if exporter_kind == "otlp":
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
            OTLPSpanExporter,
        )

        endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip()
        if not endpoint:
            logger.warning(
                "GOAT_OTEL_EXPORTER=otlp but OTEL_EXPORTER_OTLP_ENDPOINT is empty; using console exporter",
            )
            processor = BatchSpanProcessor(ConsoleSpanExporter())
        else:
            processor = BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint))
    else:
        processor = BatchSpanProcessor(ConsoleSpanExporter())
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)
    _provider_initialized = True
    logger.info("OpenTelemetry tracing initialized (exporter=%s)", exporter_kind)


@contextmanager
def otel_span(name: str, **attrs: Any) -> Generator[None, None, None]:
    if not is_otel_enabled():
        yield
        return
    init_otel_if_enabled()
    from opentelemetry import trace

    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span(name) as span:
        for k, v in attrs.items():
            span.set_attribute(str(k), str(v) if v is not None else "")
        yield


@contextmanager
def attach_request_trace_context(headers: Mapping[str, str]) -> Iterator[None]:
    """Attach W3C trace context from incoming ``traceparent`` / ``tracestate`` headers."""
    if not is_otel_enabled():
        yield
        return
    init_otel_if_enabled()
    from opentelemetry import context as otel_context
    from opentelemetry.propagate import extract

    carrier = {str(k).lower(): str(v) for k, v in headers.items()}
    ctx = extract(carrier)
    token = otel_context.attach(ctx)
    try:
        yield
    finally:
        otel_context.detach(token)
