from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import tools.run_pr_latency_gate as subject


def test_evaluate_gate_reports_budget_failures() -> None:
    failures = subject.evaluate_gate(
        subject.GateSummary(
            runs=4,
            total_avg_ms=150.0,
            total_p50_ms=120.0,
            total_p95_ms=1600.0,
            inference_chat_sample_count=4,
            inference_chat_p95_ms=1500.0,
            inference_first_token_sample_count=4,
            inference_first_token_p95_ms=500.0,
        ),
        max_total_p95_ms=1200.0,
        max_first_token_p95_ms=400.0,
    )

    assert "chat total p95 (wall clock) exceeded budget" in failures[0]
    assert "chat total p95 (system inference) exceeded budget" in failures[1]
    assert "first-token p95 (system inference) exceeded budget" in failures[2]


def test_main_runs_latency_gate_and_writes_summary(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    output = tmp_path / "pr-latency-gate.json"
    monkeypatch.setattr(
        subject.argparse.ArgumentParser,
        "parse_args",
        lambda self: SimpleNamespace(
            runs=4,
            max_total_p95_ms=1200.0,
            max_first_token_p95_ms=400.0,
            json_output=output,
        ),
    )

    assert subject.main() == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["status"] == "pass"
    assert payload["summary"]["runs"] == 4
    assert payload["budgets"]["max_total_p95_ms"] == 1200.0


def test_main_fails_when_gate_summary_exceeds_budget(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        subject.argparse.ArgumentParser,
        "parse_args",
        lambda self: SimpleNamespace(
            runs=4,
            max_total_p95_ms=1200.0,
            max_first_token_p95_ms=400.0,
            json_output=None,
        ),
    )
    monkeypatch.setattr(
        subject,
        "run_pr_latency_gate",
        lambda **_: subject.GateSummary(
            runs=4,
            total_avg_ms=150.0,
            total_p50_ms=120.0,
            total_p95_ms=1600.0,
            inference_chat_sample_count=4,
            inference_chat_p95_ms=1500.0,
            inference_first_token_sample_count=4,
            inference_first_token_p95_ms=500.0,
        ),
    )

    assert subject.main() == 1
    output = capsys.readouterr().out
    assert "PR_LATENCY_GATE_FAILED" in output
