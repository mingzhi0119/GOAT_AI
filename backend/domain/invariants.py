"""Pure checks for persisted session / chart shapes (fail fast in builders)."""

from __future__ import annotations


def chart_spec_requires_version_field(chart_spec: dict[str, object]) -> None:
    """Ensure stored chart specs carry the contract version (ChartSpecV2 / ECharts path)."""
    if "version" not in chart_spec:
        raise ValueError("chart_spec must include a version field for persistence")
