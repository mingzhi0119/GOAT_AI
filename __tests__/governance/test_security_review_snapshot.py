from __future__ import annotations

import json
from pathlib import Path

import tools.quality.security_review_snapshot as subject


def test_parse_npm_audit_reads_severity_counts_and_ids(tmp_path: Path) -> None:
    path = tmp_path / "npm-audit.json"
    path.write_text(
        json.dumps(
            {
                "metadata": {
                    "vulnerabilities": {
                        "info": 0,
                        "low": 1,
                        "moderate": 0,
                        "high": 2,
                        "critical": 0,
                        "total": 3,
                    }
                },
                "vulnerabilities": {
                    "left-pad": {
                        "via": [{"source": 101}, {"source": 202}],
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    parsed = subject.parse_npm_audit(path)

    assert parsed["vulnerability_count"] == 3
    assert parsed["severity_counts"]["high"] == 2
    assert parsed["advisory_ids"] == ["101", "202"]


def test_parse_cargo_exception_doc_collects_review_dates_and_ignored_ids(
    tmp_path: Path,
) -> None:
    path = tmp_path / "exceptions.md"
    path.write_text(
        "\n".join(
            [
                "> Last reviewed: 2026-04-11",
                "> Review again by: 2026-07-31",
                "- `RUSTSEC-2024-0411`: inherited",
                "- `RUSTSEC-2025-0057`: inherited",
            ]
        ),
        encoding="utf-8",
    )

    parsed = subject.parse_cargo_exception_doc(path)

    assert parsed["last_reviewed"] == "2026-04-11"
    assert parsed["review_again_by"] == "2026-07-31"
    assert parsed["ignored_count"] == 2


def test_build_snapshot_flags_rotation_attention_and_dependency_backlog(
    tmp_path: Path,
) -> None:
    pip_path = tmp_path / "pip-audit.json"
    pip_path.write_text(
        json.dumps(
            [
                {
                    "name": "demo",
                    "vulns": [{"id": "PYSEC-1"}],
                }
            ]
        ),
        encoding="utf-8",
    )
    npm_path = tmp_path / "npm-audit.json"
    npm_path.write_text(
        json.dumps(
            {
                "metadata": {
                    "vulnerabilities": {
                        "info": 0,
                        "low": 0,
                        "moderate": 0,
                        "high": 0,
                        "critical": 0,
                        "total": 0,
                    }
                },
                "vulnerabilities": {},
            }
        ),
        encoding="utf-8",
    )
    cargo_path = tmp_path / "cargo-audit.json"
    cargo_path.write_text(
        json.dumps({"vulnerabilities": {"list": []}}),
        encoding="utf-8",
    )
    exceptions_path = tmp_path / "exceptions.md"
    exceptions_path.write_text(
        "> Last reviewed: 2026-04-11\n> Review again by: 2026-07-31\n",
        encoding="utf-8",
    )

    snapshot = subject.build_snapshot(
        pip_audit_json=pip_path,
        npm_audit_json=npm_path,
        cargo_audit_json=cargo_path,
        desktop_cargo_exceptions_doc=exceptions_path,
        sha="abc123",
        ref_name="main",
        event_name="schedule",
        run_id="77",
        run_attempt="1",
        workflow_name="quality-trends",
        pip_exit_code=1,
        npm_exit_code=0,
        cargo_exit_code=0,
        shared_api_key_rotated_at="",
        deploy_credential_rotated_at="2026-04-01",
        desktop_signing_key_rotated_at="2025-12-01",
    )

    assert snapshot["review"]["status"] == "attention_needed"
    assert snapshot["review"]["dependency_backlog_total"] == 1
    assert "python_vulnerability_backlog" in snapshot["review"]["release_blockers"]
    credentials = snapshot["credential_rotation"]["credentials"]
    assert credentials[0]["status"] == "missing"
    assert credentials[1]["status"] == "ok"
    assert credentials[2]["status"] in {"ok", "overdue"}
