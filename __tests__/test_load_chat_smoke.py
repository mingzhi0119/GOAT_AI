from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import tools.quality.load_chat_smoke as subject


def test_build_summary_reports_percentiles() -> None:
    summary = subject._build_summary(
        [
            subject.RunSample(total_ms=100.0, first_token_ms=50.0),
            subject.RunSample(total_ms=200.0, first_token_ms=100.0),
            subject.RunSample(total_ms=300.0, first_token_ms=None),
        ]
    )

    assert summary.runs == 3
    assert summary.total_avg_ms == 200.0
    assert summary.total_p50_ms == 200.0
    assert summary.total_p95_ms == 300.0
    assert summary.first_token_avg_ms == 75.0
    assert summary.first_token_p50_ms == 50.0
    assert summary.first_token_p95_ms == 100.0


def test_check_threshold_returns_failure_message_when_budget_exceeded() -> None:
    assert (
        subject._check_threshold(
            label="total p95",
            measured_ms=2200.0,
            max_allowed_ms=2000.0,
        )
        == "total p95 exceeded budget: 2200.0 ms > 2000.0 ms"
    )
    assert (
        subject._check_threshold(
            label="total p95",
            measured_ms=1800.0,
            max_allowed_ms=2000.0,
        )
        is None
    )


def test_main_fails_when_latency_budget_is_exceeded(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        subject.argparse.ArgumentParser,
        "parse_args",
        lambda self: SimpleNamespace(
            base_url="http://127.0.0.1:62606",
            model="demo",
            runs=2,
            timeout_sec=30,
            api_key="",
            show_system_inference=False,
            max_total_p95_ms=500.0,
            max_first_token_p95_ms=150.0,
            json_output=None,
        ),
    )
    samples = iter(
        [
            subject.RunSample(total_ms=450.0, first_token_ms=120.0),
            subject.RunSample(total_ms=900.0, first_token_ms=220.0),
        ]
    )
    monkeypatch.setattr(subject, "_read_sse_sample", lambda **_: next(samples))

    assert subject.main() == 1
    output = capsys.readouterr().out
    assert "LOAD_CHAT_SMOKE_FAILED: total p95 exceeded budget" in output
    assert "LOAD_CHAT_SMOKE_FAILED: first-token p95 exceeded budget" in output


def test_main_succeeds_when_latency_budget_is_met(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        subject.argparse.ArgumentParser,
        "parse_args",
        lambda self: SimpleNamespace(
            base_url="http://127.0.0.1:62606",
            model="demo",
            runs=2,
            timeout_sec=30,
            api_key="",
            show_system_inference=True,
            max_total_p95_ms=1000.0,
            max_first_token_p95_ms=300.0,
            json_output=None,
        ),
    )
    samples = iter(
        [
            subject.RunSample(total_ms=450.0, first_token_ms=120.0),
            subject.RunSample(total_ms=900.0, first_token_ms=220.0),
        ]
    )
    monkeypatch.setattr(subject, "_read_sse_sample", lambda **_: next(samples))
    system_inference_calls: list[dict[str, object]] = []
    monkeypatch.setattr(
        subject,
        "_print_system_inference",
        lambda **kwargs: system_inference_calls.append(kwargs),
    )

    assert subject.main() == 0
    assert system_inference_calls == [
        {
            "base_url": "http://127.0.0.1:62606",
            "api_key": "",
            "timeout_sec": 30,
        }
    ]
    output = capsys.readouterr().out
    assert "LOAD_CHAT_SMOKE_FAILED" not in output


def test_write_summary_json_records_budget_status(tmp_path: Path) -> None:
    output_path = tmp_path / "performance-summary.json"

    subject.write_summary_json(
        output=output_path,
        base_url="http://127.0.0.1:62606",
        model="demo",
        summary=subject.SmokeSummary(
            runs=3,
            total_avg_ms=200.0,
            total_p50_ms=180.0,
            total_p95_ms=320.0,
            first_token_avg_ms=90.0,
            first_token_p50_ms=80.0,
            first_token_p95_ms=110.0,
        ),
        max_total_p95_ms=500.0,
        max_first_token_p95_ms=150.0,
        failures=[],
    )

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["status"] == "pass"
    assert payload["summary"]["total_p95_ms"] == 320.0
    assert payload["budgets"]["max_first_token_p95_ms"] == 150.0
