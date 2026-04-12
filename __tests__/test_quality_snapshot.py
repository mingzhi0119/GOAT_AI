from __future__ import annotations

import json
from pathlib import Path

import tools.quality.quality_snapshot as subject


def test_parse_backend_coverage_reads_statement_and_branch_metrics(
    tmp_path: Path,
) -> None:
    payload = {
        "totals": {
            "num_statements": 200,
            "covered_lines": 150,
            "missing_lines": 50,
            "percent_covered": 75.0,
            "num_branches": 40,
            "covered_branches": 30,
            "missing_branches": 10,
        }
    }
    coverage_path = tmp_path / "backend-coverage.json"
    coverage_path.write_text(json.dumps(payload), encoding="utf-8")

    parsed = subject.parse_backend_coverage(coverage_path)

    assert parsed == {
        "statements_total": 200,
        "statements_covered": 150,
        "statements_missing": 50,
        "statements_pct": 75.0,
        "branches_total": 40,
        "branches_covered": 30,
        "branches_missing": 10,
        "branches_pct": 75.0,
    }


def test_parse_frontend_lcov_aggregates_multiple_records(tmp_path: Path) -> None:
    lcov_path = tmp_path / "lcov.info"
    lcov_path.write_text(
        "\n".join(
            [
                "TN:",
                "SF:src/a.ts",
                "LF:10",
                "LH:8",
                "FNF:4",
                "FNH:3",
                "BRF:6",
                "BRH:4",
                "end_of_record",
                "TN:",
                "SF:src/b.ts",
                "LF:20",
                "LH:14",
                "FNF:6",
                "FNH:6",
                "BRF:10",
                "BRH:8",
                "end_of_record",
            ]
        ),
        encoding="utf-8",
    )

    parsed = subject.parse_frontend_lcov(lcov_path)

    assert parsed == {
        "lines_total": 30,
        "lines_covered": 22,
        "lines_pct": 73.33,
        "functions_total": 10,
        "functions_covered": 9,
        "functions_pct": 90.0,
        "branches_total": 16,
        "branches_covered": 12,
        "branches_pct": 75.0,
    }


def test_build_snapshot_includes_metadata_and_metrics(tmp_path: Path) -> None:
    backend_path = tmp_path / "backend.json"
    backend_path.write_text(
        json.dumps(
            {
                "totals": {
                    "num_statements": 10,
                    "covered_lines": 9,
                    "missing_lines": 1,
                    "percent_covered": 90.0,
                    "num_branches": 4,
                    "covered_branches": 3,
                    "missing_branches": 1,
                }
            }
        ),
        encoding="utf-8",
    )
    frontend_path = tmp_path / "lcov.info"
    frontend_path.write_text(
        "LF:10\nLH:7\nFNF:2\nFNH:2\nBRF:4\nBRH:3\n", encoding="utf-8"
    )
    security_review_path = tmp_path / "security-review.json"
    security_review_path.write_text(
        json.dumps(
            {
                "review": {
                    "status": "pass",
                    "release_blocker_count": 0,
                    "attention_count": 1,
                    "dependency_backlog_total": 2,
                }
            }
        ),
        encoding="utf-8",
    )
    performance_summary_path = tmp_path / "performance-summary.json"
    performance_summary_path.write_text(
        json.dumps(
            {
                "status": "pass",
                "summary": {
                    "runs": 10,
                    "total_p95_ms": 900.0,
                    "first_token_p95_ms": 200.0,
                },
                "failures": [],
            }
        ),
        encoding="utf-8",
    )

    snapshot = subject.build_snapshot(
        backend_coverage_json=backend_path,
        frontend_lcov=frontend_path,
        security_review_json=security_review_path,
        performance_summary_json=performance_summary_path,
        sha="abc123",
        ref_name="main",
        event_name="schedule",
        run_id="42",
        run_attempt="3",
        workflow_name="quality-trends",
    )

    assert snapshot["schema_version"] == 1
    assert snapshot["workflow"] == {
        "name": "quality-trends",
        "event_name": "schedule",
        "run_id": "42",
        "run_attempt": "3",
    }
    assert snapshot["git"] == {"sha": "abc123", "ref_name": "main"}
    metrics = snapshot["metrics"]
    assert isinstance(metrics, dict)
    assert metrics["backend_coverage"]["statements_pct"] == 90.0
    assert metrics["frontend_coverage"]["lines_pct"] == 70.0
    assert metrics["security_review"]["dependency_backlog_total"] == 2
    assert metrics["performance_smoke"]["total_p95_ms"] == 900.0
