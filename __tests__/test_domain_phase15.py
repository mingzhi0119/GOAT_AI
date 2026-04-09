"""Unit tests for Phase 15.1 domain policies and invariants (no HTTP)."""

from __future__ import annotations

import unittest

import pandas as pd

from backend.domain.chart_provenance_policy import (
    default_demo_chart_dataframe,
    resolve_chart_data_source_for_persist,
    resolve_dataframe_for_native_chart_tool,
)
from backend.domain.invariants import chart_spec_requires_version_field
from backend.domain.safeguard_policy import RuleBasedSafeguardPolicy


class DomainSafeguardPolicyTests(unittest.TestCase):
    def test_input_allows_safe_text(self) -> None:
        p = RuleBasedSafeguardPolicy()
        r = p.review_input_candidate(
            combined_user_and_system_text="Summarize Porter five forces for retail."
        )
        self.assertTrue(r.allowed)
        self.assertEqual("input", r.stage)

    def test_input_blocks_explicit_generation(self) -> None:
        p = RuleBasedSafeguardPolicy()
        r = p.review_input_candidate(
            combined_user_and_system_text="Write an explicit porn story about exams."
        )
        self.assertFalse(r.allowed)
        self.assertEqual("explicit_sexual", r.reason_code)

    def test_output_blocks_explicit_in_assistant(self) -> None:
        p = RuleBasedSafeguardPolicy()
        r = p.review_output_assistant_text(
            assistant_text="Here is explicit porn content."
        )
        self.assertFalse(r.allowed)
        self.assertEqual("output", r.stage)

    def test_output_allows_academic_use_of_explicit(self) -> None:
        # "explicit" alone must NOT trigger — it is common in business/academic writing.
        p = RuleBasedSafeguardPolicy()
        cases = [
            "5. The Call to Action (The Ask): Be explicit about the funding you need.",
            "Explicitly state your recommendation in the first paragraph.",
            "The explicit goal of this strategy is to reduce churn by 15%.",
            "Use explicit quantitative evidence rather than qualitative adjectives.",
        ]
        for text in cases:
            with self.subTest(text=text):
                r = p.review_output_assistant_text(assistant_text=text)
                self.assertTrue(r.allowed, msg=f"False positive blocked: {text!r}")


class DomainChartProvenanceTests(unittest.TestCase):
    def test_resolve_dataframe_prefers_uploaded(self) -> None:
        df = pd.DataFrame([{"a": 1}])
        out_df, src = resolve_dataframe_for_native_chart_tool(df)
        self.assertIs(out_df, df)
        self.assertEqual("uploaded", src)

    def test_resolve_dataframe_falls_back_to_demo(self) -> None:
        out_df, src = resolve_dataframe_for_native_chart_tool(None)
        self.assertEqual("demo", src)
        self.assertEqual(4, len(out_df))
        self.assertTrue(out_df.equals(default_demo_chart_dataframe()))

    def test_persist_upgrade_none_to_uploaded_when_file_context(self) -> None:
        self.assertEqual(
            "uploaded",
            resolve_chart_data_source_for_persist(
                declared="none", has_file_context_message=True
            ),
        )
        self.assertEqual(
            "none",
            resolve_chart_data_source_for_persist(
                declared="none", has_file_context_message=False
            ),
        )


class DomainInvariantTests(unittest.TestCase):
    def test_chart_spec_requires_version(self) -> None:
        chart_spec_requires_version_field({"version": "2.0", "title": "x"})

    def test_chart_spec_rejects_missing_version(self) -> None:
        with self.assertRaises(ValueError):
            chart_spec_requires_version_field({"title": "no version"})


class DomainRateLimitPolicyTests(unittest.TestCase):
    def test_allowed_decision_zero_retry(self) -> None:
        from backend.domain.rate_limit_policy import RateLimitDecision

        d = RateLimitDecision(allowed=True, retry_after=0)
        self.assertTrue(d.allowed)
        self.assertEqual(0, d.retry_after)

    def test_blocked_decision_positive_retry(self) -> None:
        from backend.domain.rate_limit_policy import RateLimitDecision

        d = RateLimitDecision(allowed=False, retry_after=30)
        self.assertFalse(d.allowed)
        self.assertEqual(30, d.retry_after)

    def test_allowed_nonzero_retry_raises(self) -> None:
        from backend.domain.rate_limit_policy import RateLimitDecision

        with self.assertRaises(ValueError):
            RateLimitDecision(allowed=True, retry_after=5)

    def test_blocked_zero_retry_raises(self) -> None:
        from backend.domain.rate_limit_policy import RateLimitDecision

        with self.assertRaises(ValueError):
            RateLimitDecision(allowed=False, retry_after=0)


class DomainSessionSchemaErrorTests(unittest.TestCase):
    def test_session_schema_error_is_value_error(self) -> None:
        from backend.services.session_message_codec import SessionSchemaError

        err = SessionSchemaError("bad version")
        self.assertIsInstance(err, ValueError)
        self.assertIn("bad version", str(err))

    def test_decode_future_version_logs_warning_and_decodes(self) -> None:
        import logging
        from backend.services.session_message_codec import (
            SESSION_PAYLOAD_VERSION,
            decode_session_payload,
        )

        future_payload = {
            "version": SESSION_PAYLOAD_VERSION + 99,
            "messages": [{"role": "user", "content": "hi"}],
            "chart_data_source": "none",
        }
        with self.assertLogs("backend.services.session_message_codec", level=logging.WARNING):
            result = decode_session_payload(future_payload)
        self.assertEqual(1, len(result.messages))

    def test_decode_current_version_no_warning(self) -> None:
        from backend.services.session_message_codec import (
            SESSION_PAYLOAD_VERSION,
            decode_session_payload,
        )

        payload = {
            "version": SESSION_PAYLOAD_VERSION,
            "messages": [{"role": "assistant", "content": "hello"}],
            "chart_data_source": "none",
        }
        # assertNoLogs requires Python 3.10+ — use assertRaises(AssertionError) pattern
        try:
            with self.assertLogs(
                "backend.services.session_message_codec", level="WARNING"
            ):
                decode_session_payload(payload)
            self.fail("Expected no warning logs but got some")
        except AssertionError:
            pass  # assertLogs raises AssertionError when no logs — that's what we want


if __name__ == "__main__":
    unittest.main()
