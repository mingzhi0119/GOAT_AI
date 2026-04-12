from __future__ import annotations

import re
from pathlib import Path

from backend.platform.prometheus_metrics import (
    EXPORTED_METRIC_FAMILIES,
    HTTP_REQUEST_DURATION_SECONDS,
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


def _normalize_metric_family(name: str) -> str:
    if name.startswith(f"{HTTP_REQUEST_DURATION_SECONDS}_"):
        return HTTP_REQUEST_DURATION_SECONDS
    return name


def _extract_metric_families(text: str) -> set[str]:
    return {_normalize_metric_family(match) for match in METRIC_TOKEN_RE.findall(text)}


def test_observability_assets_only_reference_exported_metric_families() -> None:
    asset_paths = [
        REPO_ROOT / "ops" / "observability" / "alerts" / "goat-api-alerts.yml",
        REPO_ROOT / "ops" / "observability" / "grafana" / "goat-api-dashboard.json",
        REPO_ROOT / "docs" / "operations" / "OPERATIONS.md",
        REPO_ROOT / "docs" / "operations" / "INCIDENT_TRIAGE.md",
    ]

    for path in asset_paths:
        text = path.read_text(encoding="utf-8")
        referenced = _extract_metric_families(text)
        assert referenced, f"{path} should reference at least one metric family"
        unknown = referenced - EXPORTED_METRIC_FAMILIES
        assert not unknown, (
            f"{path} references unknown metric families: {sorted(unknown)}"
        )


def test_backend_heavy_runs_observability_proof_gates() -> None:
    workflow = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8"
    )

    assert "OTel enabled-path tests" in workflow
    assert "__tests__/backend/platform/test_otel_tracing.py" in workflow
    assert "__tests__/backend/platform/test_backend_main_factory.py" in workflow
    assert "Observability asset contract" in workflow
    assert "__tests__/ops/test_observability_asset_contract.py" in workflow
