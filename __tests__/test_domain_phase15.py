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
            combined_user_and_system_text="Write an explicit pornographic story about exams."
        )
        self.assertFalse(r.allowed)
        self.assertEqual("explicit_sexual", r.reason_code)

    def test_output_blocks_explicit_in_assistant(self) -> None:
        p = RuleBasedSafeguardPolicy()
        r = p.review_output_assistant_text(
            assistant_text="Here is explicit pornographic content."
        )
        self.assertFalse(r.allowed)
        self.assertEqual("output", r.stage)


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


if __name__ == "__main__":
    unittest.main()
