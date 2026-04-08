"""Tests for optional OpenTelemetry helpers (default-off)."""
from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from goat_ai.otel_tracing import init_otel_if_enabled, is_otel_enabled, otel_span


class OtelTracingTests(unittest.TestCase):
    def test_default_disabled(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(is_otel_enabled())

    def test_init_is_noop_when_disabled(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            init_otel_if_enabled()

    def test_otel_span_noop_when_disabled(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            ran = False
            with otel_span("test.span"):
                ran = True
            self.assertTrue(ran)


if __name__ == "__main__":
    unittest.main()
