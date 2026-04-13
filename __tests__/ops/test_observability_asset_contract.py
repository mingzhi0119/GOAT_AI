from __future__ import annotations

import re
from pathlib import Path

from backend.platform.prometheus_metrics import (
    EXPORTED_METRIC_FAMILIES,
    EXPORTED_METRIC_LABELS,
    HTTP_REQUEST_DURATION_SECONDS,
    inc_chat_stream_completed,
    inc_sqlite_log_write_failure,
    record_http_request,
    render_prometheus_text,
)
from goat_ai.telemetry.telemetry_counters import (
    inc_feature_gate_denial,
    inc_knowledge_query_rewrite_applied,
    inc_knowledge_retrieval,
    inc_ollama_error,
)


def _repo_root() -> Path:
    current = Path(__file__).resolve()
    for candidate in (current.parent, *current.parents):
        if (candidate / "pyproject.toml").is_file():
            return candidate
    raise RuntimeError("Could not locate repository root from test path.")


REPO_ROOT = _repo_root()
METRIC_NAME_PATTERN = r"[a-z][a-z0-9_]*(?:_total|_seconds(?:_(?:bucket|sum|count))?)"
METRIC_TOKEN_RE = re.compile(rf"\b({METRIC_NAME_PATTERN})\b")
METRIC_SAMPLE_RE = re.compile(
    rf"^(?P<metric>{METRIC_NAME_PATTERN})(?:\{{(?P<labels>[^}}]+)\}})?\s",
    re.MULTILINE,
)
METRIC_SELECTOR_RE = re.compile(
    rf"(?P<metric>{METRIC_NAME_PATTERN})\s*\{{(?P<labels>[^}}]+)\}}"
)
METRIC_GROUP_BY_RE = re.compile(
    rf"by\s*\((?P<labels>[^)]*)\)\s*\([^\"\n]*?(?P<metric>{METRIC_NAME_PATTERN})",
    re.IGNORECASE,
)
LABEL_KEY_RE = re.compile(r"([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:=~|!~|!=|=)")
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


def _extract_selector_label_keys(label_text: str) -> set[str]:
    return {match.group(1) for match in LABEL_KEY_RE.finditer(label_text)}


def _extract_group_by_labels(label_text: str) -> set[str]:
    return {label.strip() for label in label_text.split(",") if label.strip()}


def _extract_rendered_metric_labels(text: str) -> dict[str, set[str]]:
    labels: dict[str, set[str]] = {metric: set() for metric in EXPORTED_METRIC_LABELS}
    for match in METRIC_SAMPLE_RE.finditer(text):
        metric = _normalize_metric_family(match.group("metric"))
        raw_labels = match.group("labels")
        if raw_labels:
            labels[metric].update(_extract_selector_label_keys(raw_labels))
    return labels


def _extract_asset_metric_labels(text: str) -> dict[str, set[str]]:
    labels: dict[str, set[str]] = {metric: set() for metric in EXPORTED_METRIC_LABELS}
    for match in METRIC_SELECTOR_RE.finditer(text):
        metric = _normalize_metric_family(match.group("metric"))
        labels[metric].update(_extract_selector_label_keys(match.group("labels")))
    for match in METRIC_GROUP_BY_RE.finditer(text):
        metric = _normalize_metric_family(match.group("metric"))
        labels[metric].update(_extract_group_by_labels(match.group("labels")))
    return labels


def test_rendered_prometheus_metric_families_match_exported_contract() -> None:
    rendered = _extract_metric_families(render_prometheus_text())
    assert rendered == set(EXPORTED_METRIC_FAMILIES)


def test_rendered_prometheus_metric_labels_match_exported_contract() -> None:
    record_http_request(
        method="GET", route="/api/ready", status_code=503, duration_sec=0.2
    )
    inc_chat_stream_completed()
    inc_ollama_error(
        code="INFERENCE_BACKEND_UNAVAILABLE",
        endpoint="/api/chat",
        http_status="503",
    )
    inc_sqlite_log_write_failure(operation="upsert_session", code="disk_full")
    inc_feature_gate_denial(
        feature="workbench.browse",
        gate_kind="policy",
        reason="permission_denied",
    )
    inc_knowledge_retrieval(retrieval_profile="rag3_quality", outcome="miss")
    inc_knowledge_query_rewrite_applied(retrieval_profile="rag3_quality")

    rendered = _extract_rendered_metric_labels(render_prometheus_text())
    assert rendered == {
        metric: set(labels) for metric, labels in EXPORTED_METRIC_LABELS.items()
    }


def test_observability_assets_only_reference_exported_metric_families() -> None:
    for path in APPROVED_SURFACE_PATHS:
        text = path.read_text(encoding="utf-8")
        referenced = _extract_metric_families(text)
        assert referenced, f"{path} should reference at least one metric family"
        unknown = referenced - EXPORTED_METRIC_FAMILIES
        assert not unknown, (
            f"{path} references unknown metric families: {sorted(unknown)}"
        )


def test_observability_assets_only_reference_exported_metric_labels() -> None:
    for path in APPROVED_SURFACE_PATHS:
        text = path.read_text(encoding="utf-8")
        referenced_labels = _extract_asset_metric_labels(text)
        unknown = {
            metric: sorted(labels - EXPORTED_METRIC_LABELS[metric])
            for metric, labels in referenced_labels.items()
            if labels - EXPORTED_METRIC_LABELS[metric]
        }
        assert not unknown, f"{path} references unknown metric labels: {unknown}"


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
