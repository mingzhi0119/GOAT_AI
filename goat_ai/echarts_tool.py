"""Apache ECharts migration contract: tool schema + compiler placeholder."""
from __future__ import annotations

from typing import Any

from goat_ai.chart_intent_v2 import ChartIntentV2


GENERATE_CHART_V2_SCHEMA: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "generate_chart_v2",
        "description": (
            "Create a chart intent for Apache ECharts from available tabular data. "
            "If no uploaded dataset is available, a small built-in demo dataset may be used. "
            "Return a high-level intent only; do not generate raw ECharts option fields."
        ),
        "parameters": ChartIntentV2.model_json_schema(),
    },
}


def parse_chart_intent_v2(arguments: dict[str, Any]) -> ChartIntentV2:
    """Validate native tool arguments against the versioned chart intent contract."""
    return ChartIntentV2.model_validate(arguments)
