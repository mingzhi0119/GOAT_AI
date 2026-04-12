"""Pure Python compiler from ChartIntentV2 to validated Apache ECharts options."""

from __future__ import annotations

import re

import pandas as pd

from backend.models.chart_v2 import ChartMetaV2, ChartSpecV2
from goat_ai.charts.chart_intent_v2 import (
    AggregateOp,
    ChartIntentFilterV2,
    ChartIntentSeriesV2,
    ChartIntentV2,
)

_MAX_ROWS = 50
_MAX_CATEGORY_ROWS = 20


def _normalize_token(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.strip().lower())


def _column_lookup(df: pd.DataFrame) -> dict[str, str]:
    return {_normalize_token(str(col)): str(col) for col in df.columns}


def resolve_column_name(df: pd.DataFrame, raw_name: str | None) -> str | None:
    if raw_name is None:
        return None
    candidate = raw_name.strip()
    if not candidate:
        return None

    available = [str(col) for col in df.columns]
    if candidate in available:
        return candidate

    normalized = _normalize_token(candidate)
    if not normalized:
        return None

    lookup = _column_lookup(df)
    if normalized in lookup:
        return lookup[normalized]

    for key, actual in lookup.items():
        if normalized in key or key in normalized:
            return actual
    return None


def _numeric_columns(df: pd.DataFrame) -> list[str]:
    return [str(col) for col in df.columns if pd.api.types.is_numeric_dtype(df[col])]


def _temporal_columns(df: pd.DataFrame) -> list[str]:
    results: list[str] = []
    for col in df.columns:
        series = df[col]
        if pd.api.types.is_datetime64_any_dtype(series):
            results.append(str(col))
            continue
        if pd.api.types.is_numeric_dtype(series):
            continue
        parsed = pd.to_datetime(series, errors="coerce", format="mixed")
        if parsed.notna().sum() >= max(3, int(len(series) * 0.6)):
            results.append(str(col))
    return results


def _apply_filters(
    df: pd.DataFrame,
    filters: list[ChartIntentFilterV2],
    warnings: list[str],
) -> pd.DataFrame:
    filtered = df.copy()
    for item in filters:
        column = resolve_column_name(filtered, item.column)
        if column is None:
            warnings.append(f"Skipped unknown filter column: {item.column}")
            continue

        value = item.value
        try:
            if item.operator == "eq":
                filtered = filtered[filtered[column] == value]
            elif item.operator == "neq":
                filtered = filtered[filtered[column] != value]
            elif item.operator == "gt":
                filtered = filtered[filtered[column] > value]
            elif item.operator == "gte":
                filtered = filtered[filtered[column] >= value]
            elif item.operator == "lt":
                filtered = filtered[filtered[column] < value]
            elif item.operator == "lte":
                filtered = filtered[filtered[column] <= value]
            elif item.operator == "in" and isinstance(value, list):
                filtered = filtered[filtered[column].isin(value)]
        except Exception:
            warnings.append(f"Skipped invalid filter on column: {column}")
    return filtered


def _infer_x_key(
    df: pd.DataFrame, requested_x_key: str, series_keys: list[str]
) -> str | None:
    resolved = resolve_column_name(df, requested_x_key)
    if resolved:
        return resolved

    temporal = _temporal_columns(df)
    if temporal:
        return temporal[0]

    non_numeric = [
        str(col) for col in df.columns if str(col) not in _numeric_columns(df)
    ]
    for candidate in non_numeric:
        if candidate not in series_keys:
            return candidate
    columns = [str(col) for col in df.columns]
    return columns[0] if columns else None


def _repair_series(
    df: pd.DataFrame,
    intent_series: list[ChartIntentSeriesV2],
    x_key: str,
    warnings: list[str],
) -> list[ChartIntentSeriesV2]:
    numeric = [col for col in _numeric_columns(df) if col != x_key]
    resolved: list[ChartIntentSeriesV2] = []
    for series in intent_series:
        match = resolve_column_name(df, series.key)
        if match and match != x_key and match in numeric:
            resolved.append(
                ChartIntentSeriesV2(
                    key=match,
                    name=series.name or match,
                    aggregate=series.aggregate,
                )
            )
        else:
            warnings.append(f"Skipped invalid series: {series.key}")

    if resolved:
        return resolved[:3]

    fallback = numeric[:3]
    if not fallback:
        return []
    warnings.append("Series were repaired from available numeric columns.")
    return [ChartIntentSeriesV2(key=col, name=col, aggregate="sum") for col in fallback]


def _coerce_time_grain(df: pd.DataFrame, x_key: str, time_grain: str) -> pd.Series:
    series = df[x_key]
    parsed = pd.to_datetime(series, errors="coerce", format="mixed")
    if parsed.notna().sum() < max(3, int(len(series) * 0.6)):
        return series.astype(str)

    grain = time_grain
    if grain == "auto":
        grain = "month"
    if grain == "day":
        return parsed.dt.strftime("%Y-%m-%d")
    if grain == "week":
        return parsed.dt.to_period("W").astype(str)
    if grain == "month":
        return parsed.dt.to_period("M").astype(str)
    if grain == "quarter":
        return parsed.dt.to_period("Q").astype(str)
    if grain == "year":
        return parsed.dt.to_period("Y").astype(str)
    return series.astype(str)


def _agg_name(series: ChartIntentSeriesV2) -> str:
    op = "sum" if series.aggregate == "none" else series.aggregate
    return f"{series.key}__{op}"


def _build_aggregation_spec(
    series_list: list[ChartIntentSeriesV2],
) -> dict[str, tuple[str, str]]:
    spec: dict[str, tuple[str, str]] = {}
    for item in series_list:
        op: AggregateOp = "sum" if item.aggregate == "none" else item.aggregate
        pandas_op = "mean" if op == "avg" else op
        spec[_agg_name(item)] = (item.key, pandas_op)
    return spec


def _prepare_dataset(
    df: pd.DataFrame, intent: ChartIntentV2, warnings: list[str]
) -> tuple[list[dict[str, object]], str, list[ChartIntentSeriesV2], bool]:
    working = _apply_filters(df, intent.filters, warnings)
    if working.empty:
        warnings.append("Filters produced no rows; chart skipped.")
        return [], "", [], False

    x_key = _infer_x_key(working, intent.x_key, [item.key for item in intent.series])
    if x_key is None:
        warnings.append("Could not infer x-axis column.")
        return [], "", [], False

    series_list = _repair_series(working, intent.series, x_key, warnings)
    if not series_list:
        warnings.append("No drawable numeric series were found.")
        return [], x_key, [], False

    working = working.copy()
    if intent.time_grain != "none":
        # Single-step column assign (avoids pandas 3.x chained-assignment FutureWarning).
        working.loc[:, x_key] = _coerce_time_grain(working, x_key, intent.time_grain)

    truncated = False
    aggregate = any(
        item.aggregate != "none" for item in series_list
    ) or intent.chart_type in {
        "bar",
        "stacked_bar",
        "pie",
        "area",
    }

    if aggregate:
        grouped = (
            working.groupby(x_key, dropna=False)
            .agg(**_build_aggregation_spec(series_list))
            .reset_index()
        )
    else:
        grouped = working[[x_key, *[item.key for item in series_list]]].copy()

    if intent.sort_by:
        resolved_sort = resolve_column_name(grouped, intent.sort_by)
        sort_column = resolved_sort or intent.sort_by
        if sort_column in grouped.columns and intent.sort_direction != "none":
            grouped = grouped.sort_values(
                sort_column, ascending=intent.sort_direction == "asc"
            )
        elif sort_column not in grouped.columns:
            warnings.append(f"Skipped unknown sort field: {intent.sort_by}")

    row_limit = (
        _MAX_ROWS
        if intent.chart_type in {"line", "area", "scatter"}
        else _MAX_CATEGORY_ROWS
    )
    effective_top_n = intent.top_n or row_limit
    if len(grouped) > effective_top_n:
        grouped = grouped.head(effective_top_n)
        truncated = True

    dataset = grouped.fillna("").to_dict(orient="records")
    return dataset, x_key, series_list, truncated


def _series_label(item: ChartIntentSeriesV2) -> str:
    return item.name or item.key


def _build_common_option(
    *,
    title: str,
    x_key: str,
    series_list: list[ChartIntentSeriesV2],
    dataset: list[dict[str, object]],
) -> dict[str, object]:
    return {
        "title": {"text": title},
        "tooltip": {"trigger": "axis"},
        "legend": {"data": [_series_label(item) for item in series_list]},
        "dataset": {"source": dataset},
        "xAxis": {"type": "category", "name": x_key},
        "yAxis": {"type": "value"},
    }


def _build_option(
    *,
    intent: ChartIntentV2,
    x_key: str,
    series_list: list[ChartIntentSeriesV2],
    dataset: list[dict[str, object]],
) -> dict[str, object]:
    title = intent.title.strip() or ", ".join(
        _series_label(item) for item in series_list
    )

    if intent.chart_type == "pie":
        item = series_list[0]
        value_key = (
            _agg_name(item)
            if any(key.startswith(f"{item.key}__") for key in dataset[0].keys())
            else item.key
        )
        return {
            "title": {"text": title},
            "tooltip": {"trigger": "item"},
            "legend": {"orient": "vertical", "left": "left"},
            "dataset": {"source": dataset},
            "series": [
                {
                    "type": "pie",
                    "radius": "60%",
                    "encode": {"itemName": x_key, "value": value_key},
                }
            ],
        }

    option = _build_common_option(
        title=title, x_key=x_key, series_list=series_list, dataset=dataset
    )

    chart_type = "bar" if intent.chart_type == "stacked_bar" else intent.chart_type
    if chart_type == "area":
        chart_type = "line"

    option["series"] = []
    dataset_keys = set(dataset[0].keys()) if dataset else set()
    for item in series_list:
        data_key = _agg_name(item) if _agg_name(item) in dataset_keys else item.key
        series_option: dict[str, object] = {
            "type": chart_type,
            "name": _series_label(item),
            "encode": {"x": x_key, "y": data_key},
        }
        if intent.chart_type == "stacked_bar":
            series_option["stack"] = "total"
        if intent.chart_type == "area":
            series_option["areaStyle"] = {}
            series_option["smooth"] = True
        option["series"].append(series_option)
    return option


def compile_chart_spec_v2(
    df: pd.DataFrame, intent: ChartIntentV2
) -> ChartSpecV2 | None:
    """Compile a high-level chart intent into a safe Apache ECharts payload."""
    warnings: list[str] = []
    dataset, x_key, series_list, truncated = _prepare_dataset(df, intent, warnings)
    if not dataset or not x_key or not series_list:
        return None

    option = _build_option(
        intent=intent,
        x_key=x_key,
        series_list=series_list,
        dataset=dataset,
    )
    return ChartSpecV2(
        kind=intent.chart_type,
        title=intent.title.strip() or option["title"]["text"],
        description=intent.description,
        dataset=dataset,
        option=option,
        meta=ChartMetaV2(
            row_count=len(dataset),
            truncated=truncated,
            warnings=warnings,
            source_columns=[str(col) for col in df.columns],
        ),
    )
