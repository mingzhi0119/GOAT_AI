from __future__ import annotations

import json
from pathlib import Path

import pytest

import tools.desktop.installed_windows_desktop_fault_smoke as subject
from tools.desktop import packaged_shell_fault_smoke as packaged_smoke


def test_registry_helpers_degrade_gracefully_without_winreg(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(subject, "winreg", None)
    monkeypatch.setattr(subject, "UNINSTALL_ROOTS", ())

    assert subject._iter_uninstall_entries() == []
    subject._clear_install_state_registry()


def test_match_uninstall_entry_uses_install_root(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    install_root = tmp_path / "installed-app"
    install_root.mkdir()
    monkeypatch.setattr(
        subject,
        "_iter_uninstall_entries",
        lambda: [
            {
                "display_name": "GOAT AI",
                "install_location": f"{install_root}\\",
                "uninstall_string": "MsiExec.exe /X{ABC}",
                "quiet_uninstall_string": "",
            }
        ],
    )

    entry = subject._match_uninstall_entry(install_root)

    assert entry["uninstall_string"] == "MsiExec.exe /X{ABC}"


def test_install_desktop_artifact_builds_nsis_silent_install(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    installer = tmp_path / "setup.exe"
    installer.write_text("", encoding="utf-8")
    artifact_dir = tmp_path / "artifacts"
    captured: dict[str, object] = {}

    monkeypatch.setattr(subject, "_clear_install_state_registry", lambda: None)

    def fake_run_process(**kwargs: object) -> int:
        captured["args"] = kwargs["args"]
        captured["cwd"] = kwargs["cwd"]
        return 0

    monkeypatch.setattr(subject, "_run_process", fake_run_process)
    monkeypatch.setattr(
        subject,
        "_discover_installed_file",
        lambda install_root, file_name: install_root / file_name,
    )

    installation = subject.install_desktop_artifact(
        installer_path=installer,
        installer_kind="nsis",
        artifact_dir=artifact_dir,
        install_timeout_sec=30,
    )

    assert captured["cwd"] == installer.parent
    assert captured["args"] == [
        str(installer),
        "/S",
        f"/D={Path(installation.install_root)}",
    ]
    assert installation.uninstall_command.endswith("uninstall.exe")


def test_build_healthy_launch_environment_uses_isolated_runtime_and_ready_skip(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv(packaged_smoke.INTERNAL_TEST_FLAG, "1")
    monkeypatch.setenv(packaged_smoke.INTERNAL_TEST_SCENARIO, "hang_before_ready")

    env, metadata = subject._build_healthy_launch_environment(
        base_dir=tmp_path / "healthy-launch",
        app_identifier=packaged_smoke.DEFAULT_WINDOWS_APP_IDENTIFIER,
    )

    assert env["GOAT_DESKTOP_BACKEND_HOST"] == "127.0.0.1"
    assert env[subject.READY_SKIP_OLLAMA_PROBE_ENV] == "1"
    assert env["GOAT_DESKTOP_APP_DATA_DIR"].endswith("com.simonbb.goatai")
    log_dir = Path(env["GOAT_LOG_DIR"])
    assert log_dir.name == "logs"
    assert log_dir.parent.name == "com.simonbb.goatai"
    assert packaged_smoke.INTERNAL_TEST_FLAG not in env
    assert packaged_smoke.INTERNAL_TEST_SCENARIO not in env
    assert Path(env["LOCALAPPDATA"]).is_dir()
    assert Path(env["APPDATA"]).is_dir()
    assert str(metadata["expected_shell_log_path"]).endswith("desktop-shell.log")


def test_shell_log_sidecar_start_count_counts_sidecar_spawns(tmp_path: Path) -> None:
    shell_log = tmp_path / "desktop-shell.log"
    shell_log.write_text(
        "\n".join(
            [
                "Starting bundled backend sidecar.",
                "Bundled backend sidecar spawned.",
                "Starting bundled backend sidecar.",
            ]
        ),
        encoding="utf-8",
    )

    assert subject._shell_log_sidecar_start_count(shell_log) == 2


def test_msi_uninstall_args_extract_product_code() -> None:
    uninstall_log = Path("uninstall.msiexec.log")

    args = subject._msi_uninstall_args(
        "MsiExec.exe /X{52B5624C-FF4C-45F1-8FCC-040618AD94CD}",
        uninstall_log,
    )

    assert args[:5] == [
        "msiexec.exe",
        "/x",
        "{52B5624C-FF4C-45F1-8FCC-040618AD94CD}",
        "/qn",
        "/norestart",
    ]
    assert args[-2:] == ["/l*v", str(uninstall_log)]


def test_main_writes_summary_json(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    artifact_dir = tmp_path / "artifacts"
    installer = tmp_path / "setup.exe"
    installer.write_text("", encoding="utf-8")
    installation = subject.DesktopInstallation(
        installer_kind="nsis",
        installer_path=str(installer),
        install_root=str(tmp_path / "install-root"),
        desktop_exe=str(tmp_path / "install-root" / "goat-ai-desktop.exe"),
        sidecar_path=str(tmp_path / "install-root" / "goat-backend.exe"),
        uninstall_command=str(tmp_path / "install-root" / "uninstall.exe"),
        install_log_path=None,
        install_stdout_path="install.stdout.log",
        install_stderr_path="install.stderr.log",
    )
    monkeypatch.setattr(
        subject,
        "_build_parser",
        lambda: _parser_with_namespace(
            installer=installer,
            installer_kind="nsis",
            artifact_dir=artifact_dir,
            scenarios=["missing_sidecar"],
            startup_timeout_sec=15.0,
            health_timeout_sec=2,
            restart_limit=1,
            backoff_ms=100,
            hang_sec=5.0,
            healthy_startup_timeout_sec=45.0,
            healthy_shutdown_timeout_sec=20.0,
            install_timeout_sec=30.0,
            uninstall_timeout_sec=30.0,
            app_identifier=packaged_smoke.DEFAULT_WINDOWS_APP_IDENTIFIER,
            workflow_role="release_evidence",
            release_ref="refs/tags/v1.3.0",
            resolved_sha="abc123",
            distribution_channel="public",
        ),
    )
    monkeypatch.setattr(subject, "install_desktop_artifact", lambda **_: installation)
    order: list[str] = []
    monkeypatch.setattr(
        subject,
        "run_installed_healthy_launch",
        lambda **_: (
            order.append("healthy_launch") or _healthy_launch_result(tmp_path=tmp_path)
        ),
    )
    monkeypatch.setattr(
        subject,
        "run_installed_fault_smoke",
        lambda **_: (
            order.append("fault_smoke")
            or [
                packaged_smoke.PackagedShellFaultResult(
                    scenario="missing_sidecar",
                    exit_code=1,
                    failure_stage="backend_spawn_failed",
                    log_path="desktop-shell.log",
                    stdout_path="stdout.log",
                    stderr_path="stderr.log",
                )
            ]
        ),
    )
    monkeypatch.setattr(
        subject,
        "uninstall_desktop_artifact",
        lambda **_: subject.UninstallResult(
            succeeded=True,
            exit_code=0,
            command="uninstall.exe /S",
            stdout_path="uninstall.stdout.log",
            stderr_path="uninstall.stderr.log",
            log_path=None,
            install_root_removed=True,
        ),
    )
    monkeypatch.setattr(subject.os, "name", "nt", raising=False)

    subject.main()

    summary = json.loads((artifact_dir / "summary.json").read_text(encoding="utf-8"))
    assert order == ["healthy_launch", "fault_smoke"]
    assert summary["status"] == "passed"
    assert summary["phase"] == "completed"
    assert summary["primary_failure_phase"] is None
    assert summary["primary_failure_error"] is None
    assert summary["config"]["healthy_startup_timeout_sec"] == 45.0
    assert summary["installation"]["installer_kind"] == "nsis"
    assert summary["installer_kind"] == "nsis"
    assert summary["workflow_context"]["workflow_role"] == "release_evidence"
    assert summary["workflow_context"]["resolved_sha"] == "abc123"
    assert summary["healthy_launch"]["status"] == "passed"
    assert summary["healthy_launch"]["ready_skip_ollama_probe"] is True
    assert summary["healthy_launch"]["ready_status"] == 200
    assert summary["healthy_launch"]["second_launch_handoff_ok"] is True
    assert summary["results"][0]["failure_stage"] == "backend_spawn_failed"
    assert summary["uninstall"]["succeeded"] is True


def test_main_writes_failed_summary_json_when_healthy_launch_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    artifact_dir = tmp_path / "artifacts"
    installer = tmp_path / "setup.exe"
    installer.write_text("", encoding="utf-8")
    installation = subject.DesktopInstallation(
        installer_kind="msi",
        installer_path=str(installer),
        install_root=str(tmp_path / "install-root"),
        desktop_exe=str(tmp_path / "install-root" / "goat-ai-desktop.exe"),
        sidecar_path=str(tmp_path / "install-root" / "goat-backend.exe"),
        uninstall_command="MsiExec.exe /X{ABC}",
        install_log_path="install.msiexec.log",
        install_stdout_path="install.stdout.log",
        install_stderr_path="install.stderr.log",
    )
    monkeypatch.setattr(
        subject,
        "_build_parser",
        lambda: _parser_with_namespace(
            installer=installer,
            installer_kind="msi",
            artifact_dir=artifact_dir,
            scenarios=["missing_sidecar"],
            startup_timeout_sec=15.0,
            health_timeout_sec=2,
            restart_limit=1,
            backoff_ms=100,
            hang_sec=5.0,
            healthy_startup_timeout_sec=45.0,
            healthy_shutdown_timeout_sec=20.0,
            install_timeout_sec=30.0,
            uninstall_timeout_sec=30.0,
            app_identifier=packaged_smoke.DEFAULT_WINDOWS_APP_IDENTIFIER,
            workflow_role="release_evidence",
            release_ref="refs/tags/v1.3.0",
            resolved_sha="abc123",
            distribution_channel="public",
        ),
    )
    monkeypatch.setattr(subject, "install_desktop_artifact", lambda **_: installation)
    monkeypatch.setattr(
        subject,
        "run_installed_healthy_launch",
        lambda **_: (_ for _ in ()).throw(
            subject.InstalledWindowsHealthyLaunchError(
                "Installed desktop reached /api/health but did not report readiness.",
                phase="healthy_launch:ready",
                result=_healthy_launch_result(
                    tmp_path=tmp_path,
                    status="failed",
                    phase="ready",
                    error="Installed desktop reached /api/health but did not report readiness.",
                    ready_status=503,
                ),
            )
        ),
    )
    monkeypatch.setattr(
        subject,
        "uninstall_desktop_artifact",
        lambda **_: subject.UninstallResult(
            succeeded=True,
            exit_code=0,
            command="MsiExec.exe /X{ABC}",
            stdout_path="uninstall.stdout.log",
            stderr_path="uninstall.stderr.log",
            log_path="uninstall.msiexec.log",
            install_root_removed=True,
        ),
    )
    monkeypatch.setattr(subject.os, "name", "nt", raising=False)

    with pytest.raises(SystemExit, match="did not report readiness"):
        subject.main()

    summary = json.loads((artifact_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary["status"] == "failed"
    assert summary["phase"] == "healthy_launch:ready"
    assert summary["primary_failure_phase"] == "healthy_launch:ready"
    assert (
        summary["primary_failure_error"]
        == "Installed desktop reached /api/health but did not report readiness."
    )
    assert summary["healthy_launch"]["status"] == "failed"
    assert summary["healthy_launch"]["phase"] == "ready"
    assert summary["healthy_launch"]["ready_status"] == 503
    assert summary["results"] == []
    assert summary["uninstall"]["succeeded"] is True


def test_main_writes_failed_summary_json_when_install_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    artifact_dir = tmp_path / "artifacts"
    installer = tmp_path / "setup.exe"
    installer.write_text("installer", encoding="utf-8")
    monkeypatch.setattr(
        subject,
        "_build_parser",
        lambda: _parser_with_namespace(
            installer=installer,
            installer_kind="nsis",
            artifact_dir=artifact_dir,
            scenarios=["missing_sidecar"],
            startup_timeout_sec=15.0,
            health_timeout_sec=2,
            restart_limit=1,
            backoff_ms=100,
            hang_sec=5.0,
            healthy_startup_timeout_sec=45.0,
            healthy_shutdown_timeout_sec=20.0,
            install_timeout_sec=30.0,
            uninstall_timeout_sec=30.0,
            app_identifier=packaged_smoke.DEFAULT_WINDOWS_APP_IDENTIFIER,
            workflow_role="fault_injection_drill",
            release_ref="main",
            resolved_sha="def456",
            distribution_channel="internal_test",
        ),
    )
    monkeypatch.setattr(
        subject,
        "install_desktop_artifact",
        lambda **_: (_ for _ in ()).throw(
            SystemExit("NSIS install failed with exit code 1.")
        ),
    )
    monkeypatch.setattr(subject.os, "name", "nt", raising=False)

    with pytest.raises(SystemExit, match="NSIS install failed"):
        subject.main()

    summary = json.loads((artifact_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary["status"] == "failed"
    assert summary["phase"] == "install"
    assert summary["error"] == "NSIS install failed with exit code 1."
    assert summary["primary_failure_phase"] == "install"
    assert summary["primary_failure_error"] == "NSIS install failed with exit code 1."
    assert summary["results"] == []
    assert summary["healthy_launch"] is None
    assert summary["uninstall"] is None
    assert summary["installer_sha256"]


def test_main_preserves_primary_failure_when_uninstall_also_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    artifact_dir = tmp_path / "artifacts"
    installer = tmp_path / "setup.exe"
    installer.write_text("", encoding="utf-8")
    installation = subject.DesktopInstallation(
        installer_kind="nsis",
        installer_path=str(installer),
        install_root=str(tmp_path / "install-root"),
        desktop_exe=str(tmp_path / "install-root" / "goat-ai-desktop.exe"),
        sidecar_path=str(tmp_path / "install-root" / "goat-backend.exe"),
        uninstall_command=str(tmp_path / "install-root" / "uninstall.exe"),
        install_log_path=None,
        install_stdout_path="install.stdout.log",
        install_stderr_path="install.stderr.log",
    )
    monkeypatch.setattr(
        subject,
        "_build_parser",
        lambda: _parser_with_namespace(
            installer=installer,
            installer_kind="nsis",
            artifact_dir=artifact_dir,
            scenarios=["missing_sidecar"],
            startup_timeout_sec=15.0,
            health_timeout_sec=2,
            restart_limit=1,
            backoff_ms=100,
            hang_sec=5.0,
            healthy_startup_timeout_sec=45.0,
            healthy_shutdown_timeout_sec=20.0,
            install_timeout_sec=30.0,
            uninstall_timeout_sec=30.0,
            app_identifier=packaged_smoke.DEFAULT_WINDOWS_APP_IDENTIFIER,
            workflow_role="fault_injection_drill",
            release_ref="main",
            resolved_sha="def456",
            distribution_channel="internal_test",
        ),
    )
    monkeypatch.setattr(subject, "install_desktop_artifact", lambda **_: installation)
    monkeypatch.setattr(
        subject,
        "run_installed_healthy_launch",
        lambda **_: _healthy_launch_result(tmp_path=tmp_path),
    )
    monkeypatch.setattr(
        subject,
        "run_installed_fault_smoke",
        lambda **_: (_ for _ in ()).throw(
            subject.InstalledWindowsFaultSmokeError(
                "Fault smoke detected missing sidecar.",
                phase="scenario:missing_sidecar",
                results=[
                    packaged_smoke.PackagedShellFaultResult(
                        scenario="missing_sidecar",
                        exit_code=1,
                        failure_stage="backend_spawn_failed",
                        log_path="desktop-shell.log",
                        stdout_path="stdout.log",
                        stderr_path="stderr.log",
                    )
                ],
            )
        ),
    )
    monkeypatch.setattr(
        subject,
        "uninstall_desktop_artifact",
        lambda **_: (_ for _ in ()).throw(
            SystemExit("NSIS uninstall failed with exit code 1.")
        ),
    )
    monkeypatch.setattr(subject.os, "name", "nt", raising=False)

    with pytest.raises(SystemExit, match="Fault smoke detected missing sidecar"):
        subject.main()

    summary = json.loads((artifact_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary["status"] == "failed"
    assert summary["phase"] == "scenario:missing_sidecar"
    assert summary["error"] == "Fault smoke detected missing sidecar."
    assert summary["primary_failure_phase"] == "scenario:missing_sidecar"
    assert summary["primary_failure_error"] == "Fault smoke detected missing sidecar."
    assert summary["uninstall"]["succeeded"] is False
    assert "uninstall failed" in summary["uninstall"]["error"].lower()


def test_main_rejects_non_windows_hosts(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    installer = tmp_path / "setup.exe"
    installer.write_text("", encoding="utf-8")
    artifact_dir = tmp_path / "artifacts"
    monkeypatch.setattr(
        subject,
        "_build_parser",
        lambda: _parser_with_namespace(
            installer=installer,
            installer_kind="nsis",
            artifact_dir=artifact_dir,
            scenarios=["missing_sidecar"],
            startup_timeout_sec=15.0,
            health_timeout_sec=2,
            restart_limit=1,
            backoff_ms=100,
            hang_sec=5.0,
            healthy_startup_timeout_sec=45.0,
            healthy_shutdown_timeout_sec=20.0,
            install_timeout_sec=30.0,
            uninstall_timeout_sec=30.0,
            app_identifier=packaged_smoke.DEFAULT_WINDOWS_APP_IDENTIFIER,
            workflow_role="release_evidence",
            release_ref="refs/tags/v1.3.0",
            resolved_sha="abc123",
            distribution_channel="public",
        ),
    )
    monkeypatch.setattr(subject.os, "name", "posix", raising=False)

    with pytest.raises(SystemExit, match="only supports Windows hosts"):
        subject.main()


def _parser_with_namespace(**kwargs: object):
    parser = subject.argparse.ArgumentParser()
    namespace = type("Args", (), kwargs)()
    parser.parse_args = lambda: namespace  # type: ignore[method-assign]
    return parser


def _healthy_launch_result(
    *,
    tmp_path: Path,
    status: str = "passed",
    phase: str = "completed",
    error: str | None = None,
    ready_status: int = 200,
) -> subject.HealthyLaunchResult:
    healthy_dir = tmp_path / "healthy-launch"
    return subject.HealthyLaunchResult(
        stdout_path=str(healthy_dir / "desktop.stdout.log"),
        stderr_path=str(healthy_dir / "desktop.stderr.log"),
        shutdown_stdout_path=str(healthy_dir / "shutdown.stdout.log"),
        shutdown_stderr_path=str(healthy_dir / "shutdown.stderr.log"),
        runtime_root=str(healthy_dir / "runtime-env"),
        app_local_data_dir=str(healthy_dir / "runtime-env" / "LocalAppData"),
        app_roaming_data_dir=str(healthy_dir / "runtime-env" / "RoamingAppData"),
        backend_host="127.0.0.1",
        backend_port=62606,
        health_url="http://127.0.0.1:62606/api/health",
        ready_url="http://127.0.0.1:62606/api/ready",
        runtime_target_url="http://127.0.0.1:62606/api/system/runtime-target",
        expected_shell_log_path=str(healthy_dir / "desktop-shell.log"),
        health_ready=True,
        ready_status=ready_status,
        ready_payload={"ready": ready_status == 200},
        runtime_target_status=200,
        runtime_target={"target": "local"},
        shell_log_path=str(healthy_dir / "desktop-shell.log"),
        shell_log_source_path=str(
            healthy_dir / "runtime-env" / "LocalAppData" / "desktop-shell.log"
        ),
        second_launch_stdout_path=str(healthy_dir / "second-launch.stdout.log"),
        second_launch_stderr_path=str(healthy_dir / "second-launch.stderr.log"),
        second_launch_exit_code=0,
        second_launch_handoff_ok=True,
        health_ready_after_second_launch=True,
        ready_status_after_second_launch=200,
        shell_log_spawn_count_before_second_launch=1,
        shell_log_spawn_count_after_second_launch=1,
        shutdown_method="taskkill_tree_force",
        shutdown_exit_code=0,
        status=status,
        phase=phase,
        error=error,
        started_at_utc="2026-04-12T00:00:00Z",
        completed_at_utc="2026-04-12T00:00:01Z",
    )
