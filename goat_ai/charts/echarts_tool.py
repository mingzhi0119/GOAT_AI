"""Apache ECharts migration contract: tool schema + compiler placeholder."""

from __future__ import annotations

from typing import Any

from goat_ai.charts.chart_intent_v2 import ChartIntentV2


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


def _first_string(*values: Any) -> str | None:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value
    return None


def normalize_chart_intent_arguments(arguments: dict[str, Any]) -> dict[str, Any]:
    """Normalize common native-tool argument aliases before validation.

    Local models sometimes infer friendlier field names such as ``data_key`` for
    series entries even when the advertised tool schema says ``key``. Normalize
    those aliases at the contract boundary so valid chart requests do not fall
    back to plain text just because the model used a near-miss key name.
    """
    normalized = dict(arguments)
    chart_type = _first_string(
        normalized.get("chart_type"),
        normalized.get("kind"),
        normalized.get("type"),
    )
    if chart_type is not None:
        normalized["chart_type"] = chart_type.replace("-", "_").replace(" ", "_")

    x_key = _first_string(
        normalized.get("x_key"),
        normalized.get("x"),
        normalized.get("xKey"),
        normalized.get("x_axis"),
        normalized.get("xAxis"),
        normalized.get("category_key"),
        normalized.get("categoryKey"),
    )
    if x_key is not None:
        normalized["x_key"] = x_key

    series = normalized.get("series")
    if isinstance(series, list):
        repaired_series: list[Any] = []
        for item in series:
            if not isinstance(item, dict):
                repaired_series.append(item)
                continue
            repaired = dict(item)
            key = _first_string(
                repaired.get("key"),
                repaired.get("data_key"),
                repaired.get("dataKey"),
                repaired.get("y_key"),
                repaired.get("yKey"),
                repaired.get("value_key"),
                repaired.get("valueKey"),
                repaired.get("field"),
                repaired.get("column"),
            )
            if key is not None:
                repaired["key"] = key
            repaired_series.append(repaired)
        normalized["series"] = repaired_series

    return normalized


def parse_chart_intent_v2(arguments: dict[str, Any]) -> ChartIntentV2:
    """Validate native tool arguments against the versioned chart intent contract."""
    return ChartIntentV2.model_validate(normalize_chart_intent_arguments(arguments))
