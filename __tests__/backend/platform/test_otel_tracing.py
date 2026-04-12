"""Tests for optional OpenTelemetry helpers, including enabled-path proof."""

from __future__ import annotations

import io
import os
import unittest
from contextlib import redirect_stderr
from unittest.mock import patch

from opentelemetry import trace

from goat_ai.telemetry.otel_tracing import (
    attach_request_trace_context,
    force_flush_otel_for_tests,
    init_otel_if_enabled,
    is_otel_enabled,
    otel_span,
    reset_otel_for_tests,
)


class OtelTracingTests(unittest.TestCase):
    def tearDown(self) -> None:
        reset_otel_for_tests()

    def test_default_disabled(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(is_otel_enabled())

    def test_init_is_noop_when_disabled(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            init_otel_if_enabled()
            self.assertIs(trace.get_tracer_provider(), trace._PROXY_TRACER_PROVIDER)  # type: ignore[attr-defined]

    def test_otel_span_noop_when_disabled(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            ran = False
            with otel_span("test.span"):
                ran = True
            self.assertTrue(ran)

    def test_enabled_console_exporter_emits_span_to_stderr(self) -> None:
        with patch.dict(
            os.environ,
            {"GOAT_OTEL_ENABLED": "1", "GOAT_OTEL_EXPORTER": "console"},
            clear=True,
        ):
            stderr = io.StringIO()
            with redirect_stderr(stderr):
                with otel_span("test.span", answer=42):
                    pass
                force_flush_otel_for_tests()
            rendered = stderr.getvalue()

        self.assertIn('"name": "test.span"', rendered)
        self.assertIn('"service.name": "goat-ai"', rendered)
        self.assertIn('"answer": "42"', rendered)

    def test_traceparent_propagates_into_child_span(self) -> None:
        with patch.dict(
            os.environ,
            {"GOAT_OTEL_ENABLED": "1", "GOAT_OTEL_EXPORTER": "console"},
            clear=True,
        ):
            stderr = io.StringIO()
            with redirect_stderr(stderr):
                with attach_request_trace_context(
                    {
                        "traceparent": "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
                    }
                ):
                    with otel_span("child.span"):
                        current = trace.get_current_span().get_span_context()
                        trace_id = current.trace_id
                force_flush_otel_for_tests()

        self.assertEqual(0x4BF92F3577B34DA6A3CE929D0E0E4736, trace_id)
        rendered = stderr.getvalue()
        self.assertIn('"parent_id": "0x00f067aa0ba902b7"', rendered)

    def test_otlp_without_endpoint_warns_and_falls_back_to_console(self) -> None:
        with patch.dict(
            os.environ,
            {"GOAT_OTEL_ENABLED": "1", "GOAT_OTEL_EXPORTER": "otlp"},
            clear=True,
        ):
            stderr = io.StringIO()
            with (
                patch("goat_ai.telemetry.otel_tracing.logger.warning") as warning,
                redirect_stderr(stderr),
            ):
                init_otel_if_enabled()
                with otel_span("fallback.span"):
                    pass
                force_flush_otel_for_tests()

        warning.assert_called_once()
        self.assertIn('"name": "fallback.span"', stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
