from __future__ import annotations

import unittest

from backend.models.chart_v2 import ChartIntentV2, ChartSpecV2
from goat_ai.charts.echarts_tool import GENERATE_CHART_V2_SCHEMA, parse_chart_intent_v2


class ChartV2ModelTests(unittest.TestCase):
    def test_parse_chart_intent_v2_accepts_basic_line_chart(self) -> None:
        intent = parse_chart_intent_v2(
            {
                "chart_type": "line",
                "title": "Revenue trend",
                "x_key": "month",
                "series": [{"key": "revenue", "name": "Revenue"}],
            }
        )

        self.assertIsInstance(intent, ChartIntentV2)
        self.assertEqual("line", intent.chart_type)
        self.assertEqual("month", intent.x_key)

    def test_generate_chart_v2_schema_uses_intent_contract(self) -> None:
        function = GENERATE_CHART_V2_SCHEMA["function"]
        parameters = function["parameters"]

        self.assertEqual("generate_chart_v2", function["name"])
        self.assertEqual("object", parameters["type"])
        self.assertIn("chart_type", parameters["properties"])
        self.assertIn("x_key", parameters["required"])

    def test_chart_spec_v2_model_accepts_echarts_payload(self) -> None:
        spec = ChartSpecV2.model_validate(
            {
                "kind": "bar",
                "title": "Revenue by region",
                "dataset": [{"region": "East", "revenue": 12}],
                "option": {"xAxis": {"type": "category"}, "yAxis": {"type": "value"}},
                "meta": {"row_count": 1, "source_columns": ["region", "revenue"]},
            }
        )

        self.assertEqual("echarts", spec.engine)
        self.assertEqual("bar", spec.kind)


if __name__ == "__main__":
    unittest.main()
