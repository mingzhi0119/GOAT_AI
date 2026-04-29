from __future__ import annotations

import unittest

import pandas as pd

from backend.models.chart_v2 import ChartIntentSeriesV2, ChartIntentV2
from backend.services.chart_compiler_v2 import compile_chart_spec_v2


class ChartCompilerV2Tests(unittest.TestCase):
    def test_compile_line_chart_repairs_columns_and_emits_echarts_option(self) -> None:
        df = pd.DataFrame(
            {
                "Order Date": ["2026-01-01", "2026-01-02", "2026-01-03"],
                "Revenue USD": [100, 120, 90],
            }
        )
        intent = ChartIntentV2(
            chart_type="line",
            title="Revenue trend",
            x_key="orderdate",
            series=[ChartIntentSeriesV2(key="revenue_usd", name="Revenue")],
            time_grain="day",
        )

        spec = compile_chart_spec_v2(df, intent)

        self.assertIsNotNone(spec)
        assert spec is not None
        self.assertEqual("echarts", spec.engine)
        self.assertEqual("line", spec.kind)
        self.assertEqual("Order Date", spec.option["xAxis"]["name"])
        self.assertEqual("line", spec.option["series"][0]["type"])

    def test_compile_line_chart_keeps_month_names_as_categories(self) -> None:
        df = pd.DataFrame({"month": ["Jan", "Feb", "Mar"], "revenue": [10, 15, 12]})
        intent = ChartIntentV2(
            chart_type="line",
            title="Revenue trend",
            x_key="month",
            series=[ChartIntentSeriesV2(key="revenue", name="Revenue")],
        )

        spec = compile_chart_spec_v2(df, intent)

        self.assertIsNotNone(spec)
        assert spec is not None
        self.assertEqual(
            [
                {"month": "Jan", "revenue": 10},
                {"month": "Feb", "revenue": 15},
                {"month": "Mar", "revenue": 12},
            ],
            spec.dataset,
        )

    def test_compile_stacked_bar_chart_aggregates_and_truncates(self) -> None:
        df = pd.DataFrame(
            {
                "region": ["East", "East", "West", "West", "North", "South"],
                "revenue": [10, 12, 7, 8, 5, 6],
                "profit": [2, 3, 1, 2, 1, 1],
            }
        )
        intent = ChartIntentV2(
            chart_type="stacked_bar",
            title="Regional performance",
            x_key="region",
            series=[
                ChartIntentSeriesV2(key="revenue", aggregate="sum"),
                ChartIntentSeriesV2(key="profit", aggregate="sum"),
            ],
            sort_by="revenue__sum",
            sort_direction="desc",
            top_n=3,
            stack=True,
        )

        spec = compile_chart_spec_v2(df, intent)

        self.assertIsNotNone(spec)
        assert spec is not None
        self.assertTrue(spec.meta.truncated)
        self.assertLessEqual(len(spec.dataset), 3)
        self.assertEqual("bar", spec.option["series"][0]["type"])
        self.assertEqual("total", spec.option["series"][0]["stack"])

    def test_compile_pie_chart_uses_single_series_and_filter(self) -> None:
        df = pd.DataFrame(
            {
                "region": ["East", "West", "East"],
                "revenue": [10, 12, 8],
            }
        )
        intent = ChartIntentV2(
            chart_type="pie",
            title="Revenue share",
            x_key="region",
            series=[ChartIntentSeriesV2(key="revenue", aggregate="sum")],
            filters=[],
        )

        spec = compile_chart_spec_v2(df, intent)

        self.assertIsNotNone(spec)
        assert spec is not None
        self.assertEqual("pie", spec.option["series"][0]["type"])
        self.assertIn("dataset", spec.option)


if __name__ == "__main__":
    unittest.main()
