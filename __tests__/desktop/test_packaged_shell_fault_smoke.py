from __future__ import annotations

import json
from pathlib import Path

import pytest

import tools.desktop.packaged_shell_fault_smoke as subject


def test_build_fault_smoke_environment_isolates_appdata_and_enables_hooks(
    tmp_path: Path,
) -> None:
    env = subject.build_fault_smoke_environment(
        base_dir=tmp_path,
        scenario="exit_before_ready",
        health_timeout_sec=2,
        restart_limit=1,
        backoff_ms=100,
        hang_sec=5.0,
        app_identifier=subject.DEFAULT_WINDOWS_APP_IDENTIFIER,
    )

    assert env["LOCALAPPDATA"].startswith(str(tmp_path))
    assert env["APPDATA"].startswith(str(tmp_path))
    assert env["GOAT_DESKTOP_BACKEND_HOST"] == "127.0.0.1"
    assert env["GOAT_DESKTOP_APP_DATA_DIR"].endswith("com.simonbb.goatai")
    assert env["GOAT_DESKTOP_SHELL_LOG_PATH"].endswith("desktop-shell.log")
    assert env[subject.INTERNAL_TEST_FLAG] == "1"
    assert env[subject.INTERNAL_TEST_SCENARIO] == "exit_before_ready"
    assert env[subject.INTERNAL_TEST_HEALTH_TIMEOUT_SEC] == "2"
    assert env[subject.INTERNAL_TEST_RESTART_LIMIT] == "1"
    assert env[subject.INTERNAL_TEST_BACKOFF_MS] == "100"
    assert env[subject.INTERNAL_TEST_HANG_SEC] == "5.0"


def test_discover_desktop_log_finds_nested_shell_log(tmp_path: Path) -> None:
    log_path = tmp_path / "LocalAppData" / "GOAT AI" / "logs" / "desktop-shell.log"
    log_path.parent.mkdir(parents=True)
    log_path.write_text("hello", encoding="utf-8")

    assert subject.discover_desktop_log(tmp_path) == log_path


def test_fallback_desktop_log_path_uses_localappdata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LOCALAPPDATA", "C:/Users/test/AppData/Local")

    assert subject.fallback_desktop_log_path("com.example.goat") == Path(
        "C:/Users/test/AppData/Local/com.example.goat/logs/desktop-shell.log"
    )


def test_extract_log_delta_prefers_newly_appended_bytes(tmp_path: Path) -> None:
    log_path = tmp_path / "desktop-shell.log"
    log_path.write_bytes(b"before\nafter\n")

    assert subject.extract_log_delta(log_path, b"before\n") == b"after\n"
    assert subject.extract_log_delta(log_path, b"mismatch") == b"before\nafter\n"


def test_validate_fault_smoke_log_requires_nonzero_exit_and_expected_stage() -> None:
    log_text = (
        "GOAT desktop startup issue [backend_spawn_failed]\n"
        "Retrying before window reveal after 100 ms backoff (next attempt 2/2).\n"
    )

    assert (
        subject.validate_fault_smoke_log(
            scenario="missing_sidecar",
            exit_code=1,
            log_text=log_text,
        )
        == "backend_spawn_failed"
    )

    with pytest.raises(SystemExit, match="unexpectedly exited cleanly"):
        subject.validate_fault_smoke_log(
            scenario="missing_sidecar",
            exit_code=0,
            log_text=log_text,
        )

    with pytest.raises(SystemExit, match="expected failure stage"):
        subject.validate_fault_smoke_log(
            scenario="hang_before_ready",
            exit_code=1,
            log_text=log_text,
        )


def test_main_writes_summary_json(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    artifact_dir = tmp_path / "artifacts"
    desktop_exe = tmp_path / "goat-ai-desktop.exe"
    sidecar = tmp_path / "goat-backend.exe"
    desktop_exe.write_text("", encoding="utf-8")
    sidecar.write_text("", encoding="utf-8")
    monkeypatch.setattr(
        subject,
        "_build_parser",
        lambda: _parser_with_namespace(
            desktop_exe=desktop_exe,
            sidecar=sidecar,
            artifact_dir=artifact_dir,
            scenarios=["missing_sidecar"],
            startup_timeout_sec=15.0,
            health_timeout_sec=2,
            restart_limit=1,
            backoff_ms=100,
            hang_sec=5.0,
            app_identifier=subject.DEFAULT_WINDOWS_APP_IDENTIFIER,
        ),
    )
    monkeypatch.setattr(
        subject,
        "run_fault_scenario",
        lambda **kwargs: subject.PackagedShellFaultResult(
            scenario=kwargs["scenario"],
            exit_code=1,
            failure_stage="backend_spawn_failed",
            log_path="desktop-shell.log",
            stdout_path="stdout.log",
            stderr_path="stderr.log",
        ),
    )

    subject.main()

    summary = json.loads((artifact_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary["status"] == "passed"
    assert summary["phase"] == "completed"
    assert summary["desktop_exe"] == str(desktop_exe.resolve())
    assert summary["sidecar_path"] == str(sidecar.resolve())
    assert summary["config"]["scenarios"] == ["missing_sidecar"]
    assert summary["config"]["startup_timeout_sec"] == 15.0
    assert summary["results"][0]["scenario"] == "missing_sidecar"
    assert summary["results"][0]["status"] == "passed"


def test_main_writes_failed_summary_json(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    artifact_dir = tmp_path / "artifacts"
    desktop_exe = tmp_path / "goat-ai-desktop.exe"
    sidecar = tmp_path / "goat-backend.exe"
    desktop_exe.write_text("", encoding="utf-8")
    sidecar.write_text("", encoding="utf-8")
    failed_result = subject.PackagedShellFaultResult(
        scenario="hang_before_ready",
        stdout_path="stdout.log",
        stderr_path="stderr.log",
        status="failed",
        error="timed out",
    )
    monkeypatch.setattr(
        subject,
        "_build_parser",
        lambda: _parser_with_namespace(
            desktop_exe=desktop_exe,
            sidecar=sidecar,
            artifact_dir=artifact_dir,
            scenarios=["hang_before_ready"],
            startup_timeout_sec=15.0,
            health_timeout_sec=2,
            restart_limit=1,
            backoff_ms=100,
            hang_sec=5.0,
            app_identifier=subject.DEFAULT_WINDOWS_APP_IDENTIFIER,
        ),
    )
    monkeypatch.setattr(
        subject,
        "run_fault_scenario",
        lambda **kwargs: (_ for _ in ()).throw(
            subject.PackagedShellFaultScenarioError(
                "timed out",
                result=failed_result,
            )
        ),
    )

    with pytest.raises(SystemExit, match="timed out"):
        subject.main()

    summary = json.loads((artifact_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary["status"] == "failed"
    assert summary["phase"] == "scenario:hang_before_ready"
    assert summary["error"] == "timed out"
    assert summary["results"][0]["status"] == "failed"
    assert summary["results"][0]["scenario"] == "hang_before_ready"


def _parser_with_namespace(**kwargs: object):
    parser = subject.argparse.ArgumentParser()
    namespace = type("Args", (), kwargs)()
    parser.parse_args = lambda: namespace  # type: ignore[method-assign]
    return parser
