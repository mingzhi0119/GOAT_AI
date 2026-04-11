from __future__ import annotations
from pathlib import Path

import scripts.desktop_smoke as subject


def test_build_sidecar_command_includes_module_and_data_root(tmp_path: Path) -> None:
    command = subject.build_sidecar_command(
        host="127.0.0.1",
        port=62606,
        data_root=tmp_path / "desktop-data",
    )

    assert command[:3] == [subject.sys.executable, "-m", "goat_ai.desktop_sidecar"]
    assert "--data-root" in command
    assert str(tmp_path / "desktop-data") in command


def test_wait_for_health_retries_until_success(monkeypatch) -> None:
    statuses = iter([(503, None), (503, None), (200, {"status": "ok"})])
    monkeypatch.setattr(
        subject,
        "_request_json",
        lambda url, headers, timeout_sec=2.0: next(statuses),
    )
    sleeps: list[float] = []
    monkeypatch.setattr(subject.time, "sleep", lambda seconds: sleeps.append(seconds))

    ready = subject.wait_for_health(
        base_url="http://127.0.0.1:62606",
        headers={},
        timeout_sec=1.0,
    )

    assert ready is True
    assert sleeps == [0.25, 0.25]


def test_build_failure_diagnostic_mentions_health_ready_and_runtime_target() -> None:
    message = subject.build_failure_diagnostic(
        base_url="http://127.0.0.1:62606",
        ready_status=503,
        runtime_target={"target": "local"},
    )

    assert "/api/health" in message
    assert "503" in message
    assert "runtime" in message.lower()


def test_run_desktop_smoke_starts_process_waits_and_terminates(monkeypatch) -> None:
    lifecycle: list[str] = []

    class _FakeProcess:
        def terminate(self) -> None:
            lifecycle.append("terminate")

        def wait(self, timeout: float) -> None:
            lifecycle.append(f"wait:{timeout}")

    request_responses = iter(
        [
            (200, {"status": "ok"}),
            (200, {"status": "ready"}),
            (200, {"target": "local"}),
        ]
    )
    monkeypatch.setattr(
        subject.subprocess,
        "Popen",
        lambda *args, **kwargs: lifecycle.append("spawn") or _FakeProcess(),
    )
    monkeypatch.setattr(
        subject,
        "_request_json",
        lambda url, headers, timeout_sec=2.0: next(request_responses),
    )

    result = subject.run_desktop_smoke(
        host="127.0.0.1",
        port=62606,
        timeout_sec=0.5,
    )

    assert result.health_ready is True
    assert result.ready_status == 200
    assert result.runtime_target == {"target": "local"}
    assert lifecycle == ["spawn", "terminate", "wait:5"]


def test_main_exits_with_diagnostic_when_health_never_becomes_ready(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        subject,
        "_build_parser",
        lambda: _parser_with_namespace(
            host="127.0.0.1",
            port=62606,
            timeout_sec=0.1,
            api_key="",
        ),
    )
    monkeypatch.setattr(
        subject,
        "run_desktop_smoke",
        lambda **_: subject.DesktopSmokeResult(
            health_ready=False,
            ready_status=503,
            runtime_target={"target": "local"},
        ),
    )

    try:
        subject.main()
    except SystemExit as exc:
        assert "api/health" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("Expected SystemExit for failed desktop smoke")


def _parser_with_namespace(**kwargs: object):
    parser = subject.argparse.ArgumentParser()
    namespace = type("Args", (), kwargs)()
    parser.parse_args = lambda: namespace  # type: ignore[method-assign]
    return parser
