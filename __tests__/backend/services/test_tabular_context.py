"""Unit tests for tabular context extraction boundary."""

from __future__ import annotations

import unittest

import pandas as pd

from backend.models.chat import ChatMessage
from backend.services.tabular_context import EmbeddedCsvTabularExtractor


class EmbeddedCsvTabularExtractorTests(unittest.TestCase):
    def test_extracts_first_user_csv_block(self) -> None:
        ext = EmbeddedCsvTabularExtractor()
        messages = [
            ChatMessage(role="user", content="hello"),
            ChatMessage(
                role="user",
                content=(
                    "ctx\n\nCHART_DATA_CSV:\n```\nmonth,revenue\nJan,10\nFeb,12\n```\n"
                ),
            ),
        ]
        df = ext.extract_dataframe(messages)
        self.assertIsNotNone(df)
        assert df is not None  # narrow for type checker
        pd.testing.assert_frame_equal(
            df.reset_index(drop=True),
            pd.DataFrame({"month": ["Jan", "Feb"], "revenue": [10, 12]}),
        )

    def test_returns_none_when_no_block(self) -> None:
        ext = EmbeddedCsvTabularExtractor()
        self.assertIsNone(
            ext.extract_dataframe([ChatMessage(role="user", content="no csv here")]),
        )

    def test_returns_none_for_non_user_messages_only(self) -> None:
        ext = EmbeddedCsvTabularExtractor()
        block = "CHART_DATA_CSV:\n```\na,b\n1,2\n```"
        self.assertIsNone(
            ext.extract_dataframe([ChatMessage(role="assistant", content=block)]),
        )

    def test_prioritizes_file_context_flagged_user_messages(self) -> None:
        ext = EmbeddedCsvTabularExtractor()
        plain_first = ChatMessage(
            role="user",
            content="CHART_DATA_CSV:\n```\nmonth,revenue\nJan,1\n```",
        )
        flagged_second = ChatMessage(
            role="user",
            content="CHART_DATA_CSV:\n```\nmonth,revenue\nFeb,2\n```",
            file_context=True,
        )
        df = ext.extract_dataframe([plain_first, flagged_second])
        self.assertIsNotNone(df)
        assert df is not None
        self.assertEqual(int(df.iloc[0]["revenue"]), 2)

    def test_unparseable_csv_returns_none_without_raising(self) -> None:
        ext = EmbeddedCsvTabularExtractor()
        # Empty body inside fences makes pandas raise EmptyDataError — caught in extractor.
        bad = "CHART_DATA_CSV:\n```\n\n```"
        self.assertIsNone(
            ext.extract_dataframe([ChatMessage(role="user", content=bad)]),
        )


if __name__ == "__main__":
    unittest.main()
