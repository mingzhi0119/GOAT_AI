from __future__ import annotations

import re
from pathlib import Path

from backend.platform.prometheus_metrics import (
    EXPORTED_METRIC_FAMILIES,
    HTTP_REQUEST_DURATION_SECONDS,
    render_prometheus_text,
)


def _repo_root() -> Path:
    current = Path(__file__).resolve()
    for candidate in (current.parent, *current.parents):
        if (candidate / "pyproject.toml").is_file():
            return candidate
    raise RuntimeError("Could not locate repository root from test path.")


REPO_ROOT = _repo_root()
METRIC_TOKEN_RE = re.compile(
    r"\b([a-z][a-z0-9_]*(?:_total|_seconds(?:_(?:bucket|sum|count))?))\b"
)
APPROVED_SURFACE_PATHS = [
    REPO_ROOT / "ops" / "observability" / "alerts" / "goat-api-alerts.yml",
    REPO_ROOT / "ops" / "observability" / "grafana" / "goat-api-dashboard.json",
    REPO_ROOT / "docs" / "operations" / "OPERATIONS.md",
    REPO_ROOT / "docs" / "operations" / "INCIDENT_TRIAGE.md",
]


def _normalize_metric_family(name: str) -> str:
    if name.startswith(f"{HTTP_REQUEST_DURATION_SECONDS}_"):
        return HTTP_REQUEST_DURATION_SECONDS
    return name


def _extract_metric_families(text: str) -> set[str]:
    return {_normalize_metric_family(match) for match in METRIC_TOKEN_RE.findall(text)}


def test_rendered_prometheus_metric_families_match_exported_contract() -> None:
    rendered = _extract_metric_families(render_prometheus_text())
    assert rendered == set(EXPORTED_METRIC_FAMILIES)


def test_observability_assets_only_reference_exported_metric_families() -> None:
    for path in APPROVED_SURFACE_PATHS:
        text = path.read_text(encoding="utf-8")
        referenced = _extract_metric_families(text)
        assert referenced, f"{path} should reference at least one metric family"
        unknown = referenced - EXPORTED_METRIC_FAMILIES
        assert not unknown, (
            f"{path} references unknown metric families: {sorted(unknown)}"
        )


def test_each_exported_metric_family_is_referenced_by_an_approved_surface() -> None:
    coverage: dict[str, list[str]] = {metric: [] for metric in EXPORTED_METRIC_FAMILIES}
    for path in APPROVED_SURFACE_PATHS:
        referenced = _extract_metric_families(path.read_text(encoding="utf-8"))
        for metric in sorted(referenced & EXPORTED_METRIC_FAMILIES):
            coverage[metric].append(str(path.relative_to(REPO_ROOT)))

    missing = sorted(metric for metric, paths in coverage.items() if not paths)
    assert not missing, f"Missing approved-surface coverage for metrics: {missing}"


def test_backend_heavy_runs_observability_proof_gates() -> None:
    workflow = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8"
    )

    assert "OTel enabled-path tests" in workflow
    assert "__tests__/backend/platform/test_otel_tracing.py" in workflow
    assert "__tests__/backend/platform/test_backend_main_factory.py" in workflow
    assert "Observability asset contract" in workflow
    assert "__tests__/ops/test_observability_asset_contract.py" in workflow
