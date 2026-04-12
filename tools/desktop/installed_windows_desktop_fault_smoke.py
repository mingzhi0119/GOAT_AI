from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import socket
import subprocess
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from tools.desktop import desktop_smoke as desktop_probe
from tools.desktop import packaged_shell_fault_smoke as packaged_smoke
from tools.desktop.write_desktop_release_provenance import sha256_for_path

try:
    import winreg
except ModuleNotFoundError:  # pragma: no cover - exercised on non-Windows CI
    winreg = None  # type: ignore[assignment]

PRODUCT_DISPLAY_NAME = "GOAT AI"
INSTALL_STATE_REG_PATH = r"Software\simonbb\GOAT AI"
UNINSTALL_REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Uninstall"
DESKTOP_EXE_NAME = "goat-ai-desktop.exe"
SIDECAR_EXE_NAME = "goat-backend.exe"
NSIS_UNINSTALLER_NAME = "uninstall.exe"
DEFAULT_INSTALL_TIMEOUT_SEC = 120.0
DEFAULT_UNINSTALL_TIMEOUT_SEC = 90.0
DEFAULT_HEALTHY_STARTUP_TIMEOUT_SEC = 45.0
DEFAULT_HEALTHY_SHUTDOWN_TIMEOUT_SEC = 20.0
CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
READY_SKIP_OLLAMA_PROBE_ENV = "GOAT_READY_SKIP_OLLAMA_PROBE"

UNINSTALL_ROOTS = (
    (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE) if winreg is not None else ()
)


@dataclass(frozen=True)
class DesktopInstallation:
    installer_kind: str
    installer_path: str
    install_root: str
    desktop_exe: str
    sidecar_path: str
    uninstall_command: str | None
    install_log_path: str | None
    install_stdout_path: str
    install_stderr_path: str


@dataclass(frozen=True)
class UninstallResult:
    stdout_path: str
    stderr_path: str
    succeeded: bool = False
    exit_code: int | None = None
    command: str | None = None
    log_path: str | None = None
    install_root_removed: bool = False
    status: str = "passed"
    error: str | None = None


@dataclass(frozen=True)
class HealthyLaunchResult:
    stdout_path: str
    stderr_path: str
    shutdown_stdout_path: str
    shutdown_stderr_path: str
    runtime_root: str
    app_local_data_dir: str
    app_roaming_data_dir: str
    backend_host: str
    backend_port: int
    health_url: str
    ready_url: str
    runtime_target_url: str
    expected_shell_log_path: str
    health_ready: bool = False
    ready_status: int | None = None
    ready_payload: object | None = None
    runtime_target_status: int | None = None
    runtime_target: object | None = None
    shell_log_path: str | None = None
    shell_log_source_path: str | None = None
    shutdown_method: str | None = None
    shutdown_exit_code: int | None = None
    status: str = "passed"
    phase: str = "completed"
    error: str | None = None
    started_at_utc: str | None = None
    completed_at_utc: str | None = None
    ready_skip_ollama_probe: bool = True


class InstalledWindowsFaultSmokeError(SystemExit):
    def __init__(
        self,
        message: str,
        *,
        phase: str,
        results: list[packaged_smoke.PackagedShellFaultResult],
    ) -> None:
        super().__init__(message)
        self.phase = phase
        self.results = results


class InstalledWindowsHealthyLaunchError(SystemExit):
    def __init__(
        self,
        message: str,
        *,
        phase: str,
        result: HealthyLaunchResult,
    ) -> None:
        super().__init__(message)
        self.phase = phase
        self.result = result


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="installed-windows-desktop-fault-smoke",
        description=(
            "Silently install a packaged Windows desktop artifact, prove the "
            "installed app can reach health/ready once, run fault-injected startup "
            "scenarios against the installed app, then uninstall and clean up."
        ),
    )
    parser.add_argument("--installer", type=Path, required=True)
    parser.add_argument("--installer-kind", choices=("msi", "nsis"), required=True)
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument(
        "--scenario",
        action="append",
        choices=sorted(packaged_smoke.SCENARIO_EXPECTED_STAGE),
        dest="scenarios",
    )
    parser.add_argument("--startup-timeout-sec", type=float, default=15.0)
    parser.add_argument("--health-timeout-sec", type=int, default=2)
    parser.add_argument("--restart-limit", type=int, default=1)
    parser.add_argument("--backoff-ms", type=int, default=100)
    parser.add_argument("--hang-sec", type=float, default=5.0)
    parser.add_argument(
        "--healthy-startup-timeout-sec",
        type=float,
        default=DEFAULT_HEALTHY_STARTUP_TIMEOUT_SEC,
    )
    parser.add_argument(
        "--healthy-shutdown-timeout-sec",
        type=float,
        default=DEFAULT_HEALTHY_SHUTDOWN_TIMEOUT_SEC,
    )
    parser.add_argument(
        "--install-timeout-sec",
        type=float,
        default=DEFAULT_INSTALL_TIMEOUT_SEC,
    )
    parser.add_argument(
        "--uninstall-timeout-sec",
        type=float,
        default=DEFAULT_UNINSTALL_TIMEOUT_SEC,
    )
    parser.add_argument(
        "--app-identifier",
        default=packaged_smoke.DEFAULT_WINDOWS_APP_IDENTIFIER,
    )
    parser.add_argument("--workflow-role", default="unspecified")
    parser.add_argument("--release-ref", default="")
    parser.add_argument("--resolved-sha", default="")
    parser.add_argument(
        "--distribution-channel",
        default="internal_test",
        choices=("public", "internal_test"),
    )
    return parser


def utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )


def _reserve_local_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _normalize_path(value: Path | str) -> str:
    return str(Path(value).resolve()).rstrip("\\/")


def _iter_uninstall_entries() -> list[dict[str, str]]:
    if winreg is None:
        return []
    entries: list[dict[str, str]] = []
    for hive in UNINSTALL_ROOTS:
        try:
            uninstall_root = winreg.OpenKey(hive, UNINSTALL_REG_PATH)
        except FileNotFoundError:
            continue
        with uninstall_root:
            subkey_count = winreg.QueryInfoKey(uninstall_root)[0]
            for index in range(subkey_count):
                try:
                    subkey_name = winreg.EnumKey(uninstall_root, index)
                    subkey = winreg.OpenKey(uninstall_root, subkey_name)
                except OSError:
                    continue
                with subkey:
                    try:
                        display_name = str(
                            winreg.QueryValueEx(subkey, "DisplayName")[0]
                        )
                    except FileNotFoundError:
                        continue
                    install_location = ""
                    uninstall_string = ""
                    quiet_uninstall_string = ""
                    for value_name, target in (
                        ("InstallLocation", "install_location"),
                        ("UninstallString", "uninstall_string"),
                        ("QuietUninstallString", "quiet_uninstall_string"),
                    ):
                        try:
                            value = str(winreg.QueryValueEx(subkey, value_name)[0])
                        except FileNotFoundError:
                            value = ""
                        if target == "install_location":
                            install_location = value
                        elif target == "uninstall_string":
                            uninstall_string = value
                        else:
                            quiet_uninstall_string = value
                    entries.append(
                        {
                            "display_name": display_name,
                            "install_location": install_location,
                            "uninstall_string": uninstall_string,
                            "quiet_uninstall_string": quiet_uninstall_string,
                        }
                    )
    return entries


def _clear_install_state_registry() -> None:
    if winreg is None:
        return

    def delete_tree(hive: int, subkey_path: str) -> None:
        try:
            key = winreg.OpenKey(
                hive, subkey_path, 0, winreg.KEY_READ | winreg.KEY_WRITE
            )
        except FileNotFoundError:
            return
        with key:
            while True:
                try:
                    child_name = winreg.EnumKey(key, 0)
                except OSError:
                    break
                delete_tree(hive, f"{subkey_path}\\{child_name}")
        winreg.DeleteKey(hive, subkey_path)

    delete_tree(winreg.HKEY_CURRENT_USER, INSTALL_STATE_REG_PATH)


def _run_process(
    *,
    args: list[str],
    cwd: Path | None,
    env: dict[str, str] | None,
    stdout_path: Path,
    stderr_path: Path,
    timeout_sec: float,
) -> int:
    with (
        stdout_path.open("w", encoding="utf-8") as stdout_file,
        stderr_path.open("w", encoding="utf-8") as stderr_file,
    ):
        process = subprocess.Popen(  # noqa: S603
            args,
            cwd=str(cwd) if cwd else None,
            env=env,
            stdout=stdout_file,
            stderr=stderr_file,
            creationflags=CREATE_NO_WINDOW,
        )
        try:
            return int(process.wait(timeout=timeout_sec))
        except subprocess.TimeoutExpired as exc:
            process.kill()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                pass
            raise SystemExit(
                f"Command {' '.join(args)!r} did not exit within {timeout_sec} seconds."
            ) from exc


def _discover_installed_file(install_root: Path, file_name: str) -> Path:
    candidates = [path for path in install_root.rglob(file_name) if path.is_file()]
    if not candidates:
        raise SystemExit(
            f"Could not find {file_name} under installed root {install_root}."
        )
    return min(candidates, key=lambda path: len(path.parts))


def _match_uninstall_entry(install_root: Path) -> dict[str, str]:
    normalized_root = _normalize_path(install_root)
    matching_entries = [
        entry
        for entry in _iter_uninstall_entries()
        if entry["display_name"] == PRODUCT_DISPLAY_NAME
    ]
    for entry in matching_entries:
        if entry["display_name"] != PRODUCT_DISPLAY_NAME:
            continue
        install_location = entry["install_location"].strip()
        if install_location and _normalize_path(install_location) == normalized_root:
            return entry
    discovered_roots = sorted(
        {
            entry["install_location"].strip()
            for entry in matching_entries
            if entry["install_location"].strip()
        }
    )
    raise SystemExit(
        f"Could not find Windows uninstall metadata for {PRODUCT_DISPLAY_NAME} at {install_root}. "
        f"Discovered existing install roots: {discovered_roots or ['<none>']}."
    )


def install_desktop_artifact(
    *,
    installer_path: Path,
    installer_kind: str,
    artifact_dir: Path,
    install_timeout_sec: float,
) -> DesktopInstallation:
    install_root = (artifact_dir / "installed-app").resolve()
    if install_root.exists():
        shutil.rmtree(install_root, ignore_errors=True)
    install_root.mkdir(parents=True, exist_ok=True)
    install_stdout_path = artifact_dir / "install.stdout.log"
    install_stderr_path = artifact_dir / "install.stderr.log"

    _clear_install_state_registry()

    if installer_kind == "msi":
        install_log_path = artifact_dir / "install.msiexec.log"
        args = [
            "msiexec.exe",
            "/i",
            str(installer_path),
            "ALLUSERS=2",
            "MSIINSTALLPERUSER=1",
            f"INSTALLDIR={install_root}",
            "/qn",
            "/norestart",
            "/l*v",
            str(install_log_path),
        ]
        exit_code = _run_process(
            args=args,
            cwd=None,
            env=None,
            stdout_path=install_stdout_path,
            stderr_path=install_stderr_path,
            timeout_sec=install_timeout_sec,
        )
        if exit_code != 0:
            raise SystemExit(f"MSI install failed with exit code {exit_code}.")
        uninstall_entry = _match_uninstall_entry(install_root)
        uninstall_command = (
            uninstall_entry["quiet_uninstall_string"]
            or uninstall_entry["uninstall_string"]
        )
    else:
        install_log_path = None
        args = [str(installer_path), "/S", f"/D={install_root}"]
        exit_code = _run_process(
            args=args,
            cwd=installer_path.parent,
            env=None,
            stdout_path=install_stdout_path,
            stderr_path=install_stderr_path,
            timeout_sec=install_timeout_sec,
        )
        if exit_code != 0:
            raise SystemExit(f"NSIS install failed with exit code {exit_code}.")
        uninstall_command = str(
            _discover_installed_file(install_root, NSIS_UNINSTALLER_NAME)
        )

    desktop_exe = _discover_installed_file(install_root, DESKTOP_EXE_NAME)
    sidecar_path = _discover_installed_file(install_root, SIDECAR_EXE_NAME)
    return DesktopInstallation(
        installer_kind=installer_kind,
        installer_path=str(installer_path),
        install_root=str(install_root),
        desktop_exe=str(desktop_exe),
        sidecar_path=str(sidecar_path),
        uninstall_command=uninstall_command,
        install_log_path=str(install_log_path) if install_log_path else None,
        install_stdout_path=str(install_stdout_path),
        install_stderr_path=str(install_stderr_path),
    )


def _msi_uninstall_args(command: str, uninstall_log_path: Path) -> list[str]:
    guid_match = re.search(r"\{[0-9A-Fa-f-]+\}", command)
    if guid_match is None:
        raise SystemExit(
            f"Could not extract MSI product code from uninstall command {command!r}."
        )
    return [
        "msiexec.exe",
        "/x",
        guid_match.group(0),
        "/qn",
        "/norestart",
        "/l*v",
        str(uninstall_log_path),
    ]


def _remove_install_root(install_root: Path) -> bool:
    for _ in range(5):
        if not install_root.exists():
            return True
        shutil.rmtree(install_root, ignore_errors=True)
        if not install_root.exists():
            return True
        time.sleep(1)
    return not install_root.exists()


def uninstall_desktop_artifact(
    *,
    installation: DesktopInstallation,
    artifact_dir: Path,
    uninstall_timeout_sec: float,
) -> UninstallResult:
    uninstall_stdout_path = artifact_dir / "uninstall.stdout.log"
    uninstall_stderr_path = artifact_dir / "uninstall.stderr.log"
    uninstall_log_path: Path | None = None
    exit_code: int | None = None

    if installation.uninstall_command:
        if installation.installer_kind == "msi":
            uninstall_log_path = artifact_dir / "uninstall.msiexec.log"
            args = _msi_uninstall_args(
                installation.uninstall_command, uninstall_log_path
            )
            exit_code = _run_process(
                args=args,
                cwd=None,
                env=None,
                stdout_path=uninstall_stdout_path,
                stderr_path=uninstall_stderr_path,
                timeout_sec=uninstall_timeout_sec,
            )
        else:
            args = [installation.uninstall_command, "/S"]
            exit_code = _run_process(
                args=args,
                cwd=Path(installation.install_root),
                env=None,
                stdout_path=uninstall_stdout_path,
                stderr_path=uninstall_stderr_path,
                timeout_sec=uninstall_timeout_sec,
            )

    install_root_removed = _remove_install_root(Path(installation.install_root))
    _clear_install_state_registry()
    return UninstallResult(
        stdout_path=str(uninstall_stdout_path),
        stderr_path=str(uninstall_stderr_path),
        succeeded=exit_code in (None, 0),
        exit_code=exit_code,
        command=installation.uninstall_command,
        log_path=str(uninstall_log_path) if uninstall_log_path else None,
        install_root_removed=install_root_removed,
    )


def run_installed_fault_smoke(
    *,
    installation: DesktopInstallation,
    artifact_dir: Path,
    scenarios: list[str],
    startup_timeout_sec: float,
    health_timeout_sec: int,
    restart_limit: int,
    backoff_ms: int,
    hang_sec: float,
    app_identifier: str,
) -> list[packaged_smoke.PackagedShellFaultResult]:
    results: list[packaged_smoke.PackagedShellFaultResult] = []
    for scenario in scenarios:
        try:
            result = packaged_smoke.run_fault_scenario(
                desktop_exe=Path(installation.desktop_exe),
                sidecar_path=Path(installation.sidecar_path),
                artifact_dir=artifact_dir / "scenarios",
                scenario=scenario,
                startup_timeout_sec=startup_timeout_sec,
                health_timeout_sec=health_timeout_sec,
                restart_limit=restart_limit,
                backoff_ms=backoff_ms,
                hang_sec=hang_sec,
                app_identifier=app_identifier,
            )
            results.append(result)
        except packaged_smoke.PackagedShellFaultScenarioError as exc:
            results.append(exc.result)
            raise InstalledWindowsFaultSmokeError(
                str(exc),
                phase=f"scenario:{scenario}",
                results=results,
            ) from exc
    return results


def _expected_install_log_path(
    *, artifact_dir: Path, installer_kind: str
) -> str | None:
    if installer_kind == "msi":
        return str(artifact_dir / "install.msiexec.log")
    return None


def _expected_uninstall_log_path(
    *,
    artifact_dir: Path,
    installer_kind: str,
) -> str | None:
    if installer_kind == "msi":
        return str(artifact_dir / "uninstall.msiexec.log")
    return None


def _build_failed_uninstall_result(
    *,
    installation: DesktopInstallation,
    artifact_dir: Path,
    error: str,
) -> UninstallResult:
    return UninstallResult(
        stdout_path=str(artifact_dir / "uninstall.stdout.log"),
        stderr_path=str(artifact_dir / "uninstall.stderr.log"),
        command=installation.uninstall_command,
        log_path=_expected_uninstall_log_path(
            artifact_dir=artifact_dir,
            installer_kind=installation.installer_kind,
        ),
        status="failed",
        error=error,
    )


def _build_healthy_launch_environment(
    *,
    base_dir: Path,
    app_identifier: str,
) -> tuple[dict[str, str], dict[str, object]]:
    runtime_root = base_dir / "runtime-env"
    local_appdata = runtime_root / "LocalAppData"
    roaming_appdata = runtime_root / "RoamingAppData"
    local_appdata.mkdir(parents=True, exist_ok=True)
    roaming_appdata.mkdir(parents=True, exist_ok=True)
    backend_host = "127.0.0.1"
    backend_port = _reserve_local_port()

    env = os.environ.copy()
    env["LOCALAPPDATA"] = str(local_appdata)
    env["APPDATA"] = str(roaming_appdata)
    env["GOAT_DESKTOP_BACKEND_HOST"] = backend_host
    env["GOAT_DESKTOP_BACKEND_PORT"] = str(backend_port)
    env["GOAT_DESKTOP_APP_DATA_DIR"] = str(local_appdata / app_identifier)
    env["GOAT_RUNTIME_ROOT"] = env["GOAT_DESKTOP_APP_DATA_DIR"]
    env["GOAT_LOG_DIR"] = str(local_appdata / app_identifier / "logs")
    env["GOAT_LOG_PATH"] = str(local_appdata / app_identifier / "chat_logs.db")
    env["GOAT_DATA_DIR"] = str(local_appdata / app_identifier / "data")
    env[READY_SKIP_OLLAMA_PROBE_ENV] = "1"
    for name in (
        packaged_smoke.INTERNAL_TEST_FLAG,
        packaged_smoke.INTERNAL_TEST_SCENARIO,
        packaged_smoke.INTERNAL_TEST_HEALTH_TIMEOUT_SEC,
        packaged_smoke.INTERNAL_TEST_RESTART_LIMIT,
        packaged_smoke.INTERNAL_TEST_BACKOFF_MS,
        packaged_smoke.INTERNAL_TEST_HANG_SEC,
    ):
        env.pop(name, None)

    expected_shell_log_path = packaged_smoke.fallback_desktop_log_path(
        app_identifier,
        local_appdata=local_appdata,
    )
    metadata = {
        "runtime_root": str(runtime_root),
        "app_local_data_dir": env["GOAT_DESKTOP_APP_DATA_DIR"],
        "app_roaming_data_dir": str(roaming_appdata),
        "backend_host": backend_host,
        "backend_port": backend_port,
        "health_url": f"http://{backend_host}:{backend_port}/api/health",
        "ready_url": f"http://{backend_host}:{backend_port}/api/ready",
        "runtime_target_url": (
            f"http://{backend_host}:{backend_port}/api/system/runtime-target"
        ),
        "expected_shell_log_path": str(expected_shell_log_path),
    }
    return env, metadata


def _copy_shell_log(
    *,
    source_log_path: Path,
    copied_log_path: Path,
    wait_timeout_sec: float = 5.0,
) -> tuple[str, str]:
    deadline = time.monotonic() + wait_timeout_sec
    while time.monotonic() < deadline:
        if source_log_path.is_file():
            copied_log_path.parent.mkdir(parents=True, exist_ok=True)
            copied_log_path.write_bytes(source_log_path.read_bytes())
            return str(copied_log_path), str(source_log_path)
        time.sleep(0.25)
    raise SystemExit(
        f"Could not find desktop-shell.log at expected path {source_log_path}."
    )


def _healthy_launch_result_from_context(
    *,
    context: dict[str, object],
    healthy_dir: Path,
    started_at_utc: str,
    status: str,
    phase: str,
    error: str | None,
    health_ready: bool = False,
    ready_status: int | None = None,
    ready_payload: object | None = None,
    runtime_target_status: int | None = None,
    runtime_target: object | None = None,
    shell_log_path: str | None = None,
    shell_log_source_path: str | None = None,
    shutdown_method: str | None = None,
    shutdown_exit_code: int | None = None,
) -> HealthyLaunchResult:
    return HealthyLaunchResult(
        stdout_path=str(healthy_dir / "desktop.stdout.log"),
        stderr_path=str(healthy_dir / "desktop.stderr.log"),
        shutdown_stdout_path=str(healthy_dir / "shutdown.stdout.log"),
        shutdown_stderr_path=str(healthy_dir / "shutdown.stderr.log"),
        runtime_root=str(context["runtime_root"]),
        app_local_data_dir=str(context["app_local_data_dir"]),
        app_roaming_data_dir=str(context["app_roaming_data_dir"]),
        backend_host=str(context["backend_host"]),
        backend_port=int(context["backend_port"]),
        health_url=str(context["health_url"]),
        ready_url=str(context["ready_url"]),
        runtime_target_url=str(context["runtime_target_url"]),
        expected_shell_log_path=str(context["expected_shell_log_path"]),
        health_ready=health_ready,
        ready_status=ready_status,
        ready_payload=ready_payload,
        runtime_target_status=runtime_target_status,
        runtime_target=runtime_target,
        shell_log_path=shell_log_path,
        shell_log_source_path=shell_log_source_path,
        shutdown_method=shutdown_method,
        shutdown_exit_code=shutdown_exit_code,
        status=status,
        phase=phase,
        error=error,
        started_at_utc=started_at_utc,
        completed_at_utc=utc_now(),
    )


def _best_effort_kill_process_tree(process: subprocess.Popen[object]) -> None:
    if process.poll() is not None:
        return
    try:
        subprocess.run(  # noqa: S603
            ["taskkill.exe", "/PID", str(process.pid), "/T", "/F"],
            check=False,
            timeout=5,
            creationflags=CREATE_NO_WINDOW,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except (subprocess.SubprocessError, OSError):
        process.kill()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pass


def run_installed_healthy_launch(
    *,
    installation: DesktopInstallation,
    artifact_dir: Path,
    app_identifier: str,
    startup_timeout_sec: float,
    shutdown_timeout_sec: float,
) -> HealthyLaunchResult:
    healthy_dir = artifact_dir / "healthy-launch"
    healthy_dir.mkdir(parents=True, exist_ok=True)
    started_at_utc = utc_now()
    env, context = _build_healthy_launch_environment(
        base_dir=healthy_dir,
        app_identifier=app_identifier,
    )
    headers = desktop_probe.build_request_headers()
    expected_shell_log_path = Path(str(context["expected_shell_log_path"]))
    copied_shell_log_path = healthy_dir / "desktop-shell.log"
    process: subprocess.Popen[object] | None = None
    health_ready = False
    ready_status: int | None = None
    ready_payload: object | None = None
    runtime_target_status: int | None = None
    runtime_target: object | None = None
    shutdown_method: str | None = None
    shutdown_exit_code: int | None = None

    try:
        with (
            (healthy_dir / "desktop.stdout.log").open(
                "w", encoding="utf-8"
            ) as stdout_file,
            (healthy_dir / "desktop.stderr.log").open(
                "w", encoding="utf-8"
            ) as stderr_file,
        ):
            process = subprocess.Popen(  # noqa: S603
                [installation.desktop_exe],
                cwd=str(Path(installation.desktop_exe).parent),
                env=env,
                stdout=stdout_file,
                stderr=stderr_file,
                creationflags=CREATE_NO_WINDOW,
            )

            health_ready = desktop_probe.wait_for_health(
                base_url=f"http://{context['backend_host']}:{context['backend_port']}",
                headers=headers,
                timeout_sec=startup_timeout_sec,
            )
            if not health_ready:
                raise InstalledWindowsHealthyLaunchError(
                    (
                        "Installed desktop never reached /api/health during the "
                        "healthy launch proof."
                    ),
                    phase="healthy_launch:health",
                    result=_healthy_launch_result_from_context(
                        context=context,
                        healthy_dir=healthy_dir,
                        started_at_utc=started_at_utc,
                        status="failed",
                        phase="health",
                        error=(
                            "Installed desktop never reached /api/health during the "
                            "healthy launch proof."
                        ),
                    ),
                )

            ready_status, ready_payload = desktop_probe._request_json(
                str(context["ready_url"]),
                headers=headers,
            )
            runtime_target_status, runtime_target = desktop_probe._request_json(
                str(context["runtime_target_url"]),
                headers=headers,
            )
            ready_ok = ready_status == 200 and bool(
                isinstance(ready_payload, dict) and ready_payload.get("ready")
            )
            if not ready_ok:
                raise InstalledWindowsHealthyLaunchError(
                    (
                        "Installed desktop reached /api/health but did not report a "
                        "ready baseline under GOAT_READY_SKIP_OLLAMA_PROBE=1."
                    ),
                    phase="healthy_launch:ready",
                    result=_healthy_launch_result_from_context(
                        context=context,
                        healthy_dir=healthy_dir,
                        started_at_utc=started_at_utc,
                        status="failed",
                        phase="ready",
                        error=(
                            "Installed desktop reached /api/health but did not report "
                            "a ready baseline under GOAT_READY_SKIP_OLLAMA_PROBE=1."
                        ),
                        health_ready=health_ready,
                        ready_status=ready_status,
                        ready_payload=ready_payload,
                        runtime_target_status=runtime_target_status,
                        runtime_target=runtime_target,
                    ),
                )

            if process.poll() is not None:
                raise InstalledWindowsHealthyLaunchError(
                    (
                        "Installed desktop exited before the healthy launch proof "
                        "could perform controlled shutdown."
                    ),
                    phase="healthy_launch:process_exit",
                    result=_healthy_launch_result_from_context(
                        context=context,
                        healthy_dir=healthy_dir,
                        started_at_utc=started_at_utc,
                        status="failed",
                        phase="process_exit",
                        error=(
                            "Installed desktop exited before the healthy launch proof "
                            "could perform controlled shutdown."
                        ),
                        health_ready=health_ready,
                        ready_status=ready_status,
                        ready_payload=ready_payload,
                        runtime_target_status=runtime_target_status,
                        runtime_target=runtime_target,
                    ),
                )

            shutdown_exit_code = _run_process(
                args=["taskkill.exe", "/PID", str(process.pid), "/T", "/F"],
                cwd=None,
                env=None,
                stdout_path=healthy_dir / "shutdown.stdout.log",
                stderr_path=healthy_dir / "shutdown.stderr.log",
                timeout_sec=shutdown_timeout_sec,
            )
            shutdown_method = "taskkill_tree_force"
            if shutdown_exit_code != 0:
                raise InstalledWindowsHealthyLaunchError(
                    "Controlled shutdown of the healthy installed desktop failed.",
                    phase="healthy_launch:shutdown",
                    result=_healthy_launch_result_from_context(
                        context=context,
                        healthy_dir=healthy_dir,
                        started_at_utc=started_at_utc,
                        status="failed",
                        phase="shutdown",
                        error="Controlled shutdown of the healthy installed desktop failed.",
                        health_ready=health_ready,
                        ready_status=ready_status,
                        ready_payload=ready_payload,
                        runtime_target_status=runtime_target_status,
                        runtime_target=runtime_target,
                        shutdown_method=shutdown_method,
                        shutdown_exit_code=shutdown_exit_code,
                    ),
                )
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired as exc:
                raise InstalledWindowsHealthyLaunchError(
                    (
                        "Installed desktop remained alive after the healthy launch "
                        "controlled shutdown request."
                    ),
                    phase="healthy_launch:shutdown",
                    result=_healthy_launch_result_from_context(
                        context=context,
                        healthy_dir=healthy_dir,
                        started_at_utc=started_at_utc,
                        status="failed",
                        phase="shutdown",
                        error=(
                            "Installed desktop remained alive after the healthy "
                            "launch controlled shutdown request."
                        ),
                        health_ready=health_ready,
                        ready_status=ready_status,
                        ready_payload=ready_payload,
                        runtime_target_status=runtime_target_status,
                        runtime_target=runtime_target,
                        shutdown_method=shutdown_method,
                        shutdown_exit_code=shutdown_exit_code,
                    ),
                ) from exc

        shell_log_path, shell_log_source_path = _copy_shell_log(
            source_log_path=expected_shell_log_path,
            copied_log_path=copied_shell_log_path,
        )
        return _healthy_launch_result_from_context(
            context=context,
            healthy_dir=healthy_dir,
            started_at_utc=started_at_utc,
            status="passed",
            phase="completed",
            error=None,
            health_ready=health_ready,
            ready_status=ready_status,
            ready_payload=ready_payload,
            runtime_target_status=runtime_target_status,
            runtime_target=runtime_target,
            shell_log_path=shell_log_path,
            shell_log_source_path=shell_log_source_path,
            shutdown_method=shutdown_method,
            shutdown_exit_code=shutdown_exit_code,
        )
    except InstalledWindowsHealthyLaunchError:
        raise
    except SystemExit as exc:
        raise InstalledWindowsHealthyLaunchError(
            str(exc),
            phase="healthy_launch:log_capture",
            result=_healthy_launch_result_from_context(
                context=context,
                healthy_dir=healthy_dir,
                started_at_utc=started_at_utc,
                status="failed",
                phase="log_capture",
                error=str(exc),
                health_ready=health_ready,
                ready_status=ready_status,
                ready_payload=ready_payload,
                runtime_target_status=runtime_target_status,
                runtime_target=runtime_target,
                shutdown_method=shutdown_method,
                shutdown_exit_code=shutdown_exit_code,
            ),
        ) from exc
    finally:
        if process is not None:
            _best_effort_kill_process_tree(process)


def _build_summary_payload(
    *,
    installer_path: Path,
    installer_kind: str,
    artifact_dir: Path,
    workflow_role: str,
    release_ref: str,
    resolved_sha: str,
    distribution_channel: str,
    status: str,
    phase: str,
    error: str | None,
    scenarios: list[str],
    startup_timeout_sec: float,
    health_timeout_sec: int,
    restart_limit: int,
    backoff_ms: int,
    hang_sec: float,
    healthy_startup_timeout_sec: float,
    healthy_shutdown_timeout_sec: float,
    installation: DesktopInstallation | None,
    healthy_launch_result: HealthyLaunchResult | None,
    results: list[packaged_smoke.PackagedShellFaultResult],
    uninstall_result: UninstallResult | None,
    started_at_utc: str,
) -> dict[str, object]:
    return {
        "status": status,
        "phase": phase,
        "error": error,
        "started_at_utc": started_at_utc,
        "completed_at_utc": utc_now(),
        "workflow_context": {
            "workflow_role": workflow_role,
            "release_ref": release_ref or None,
            "resolved_sha": resolved_sha or None,
            "distribution_channel": distribution_channel,
        },
        "installer_kind": installer_kind,
        "installer_path": str(installer_path),
        "installer_sha256": sha256_for_path(installer_path),
        "config": {
            "scenarios": scenarios,
            "startup_timeout_sec": startup_timeout_sec,
            "health_timeout_sec": health_timeout_sec,
            "restart_limit": restart_limit,
            "backoff_ms": backoff_ms,
            "hang_sec": hang_sec,
            "healthy_startup_timeout_sec": healthy_startup_timeout_sec,
            "healthy_shutdown_timeout_sec": healthy_shutdown_timeout_sec,
        },
        "install_root": installation.install_root if installation else None,
        "desktop_exe": installation.desktop_exe if installation else None,
        "sidecar_path": installation.sidecar_path if installation else None,
        "install_stdout_path": (
            installation.install_stdout_path
            if installation
            else str(artifact_dir / "install.stdout.log")
        ),
        "install_stderr_path": (
            installation.install_stderr_path
            if installation
            else str(artifact_dir / "install.stderr.log")
        ),
        "install_log_path": (
            installation.install_log_path
            if installation
            else _expected_install_log_path(
                artifact_dir=artifact_dir,
                installer_kind=installer_kind,
            )
        ),
        "installation": asdict(installation) if installation else None,
        "healthy_launch": (
            asdict(healthy_launch_result) if healthy_launch_result else None
        ),
        "results": [asdict(result) for result in results],
        "uninstall": asdict(uninstall_result) if uninstall_result else None,
    }


def main() -> None:
    if os.name != "nt":
        raise SystemExit(
            "installed_windows_desktop_fault_smoke only supports Windows hosts."
        )

    args = _build_parser().parse_args()
    installer_path = args.installer.resolve()
    artifact_dir = args.artifact_dir.resolve()
    artifact_dir.mkdir(parents=True, exist_ok=True)
    scenarios = args.scenarios or list(packaged_smoke.SCENARIO_EXPECTED_STAGE)
    started_at_utc = utc_now()
    installation: DesktopInstallation | None = None
    healthy_launch_result: HealthyLaunchResult | None = None
    uninstall_result: UninstallResult | None = None
    results: list[packaged_smoke.PackagedShellFaultResult] = []
    status = "passed"
    phase = "completed"
    error: str | None = None
    try:
        installation = install_desktop_artifact(
            installer_path=installer_path,
            installer_kind=args.installer_kind,
            artifact_dir=artifact_dir,
            install_timeout_sec=args.install_timeout_sec,
        )
        healthy_launch_result = run_installed_healthy_launch(
            installation=installation,
            artifact_dir=artifact_dir,
            app_identifier=args.app_identifier,
            startup_timeout_sec=args.healthy_startup_timeout_sec,
            shutdown_timeout_sec=args.healthy_shutdown_timeout_sec,
        )
        results = run_installed_fault_smoke(
            installation=installation,
            artifact_dir=artifact_dir,
            scenarios=scenarios,
            startup_timeout_sec=args.startup_timeout_sec,
            health_timeout_sec=args.health_timeout_sec,
            restart_limit=args.restart_limit,
            backoff_ms=args.backoff_ms,
            hang_sec=args.hang_sec,
            app_identifier=args.app_identifier,
        )
    except InstalledWindowsHealthyLaunchError as exc:
        status = "failed"
        phase = exc.phase
        error = str(exc)
        healthy_launch_result = exc.result
    except InstalledWindowsFaultSmokeError as exc:
        status = "failed"
        phase = exc.phase
        error = str(exc)
        results = list(exc.results)
    except SystemExit as exc:
        status = "failed"
        phase = "install"
        error = str(exc)
    finally:
        if installation is not None:
            try:
                uninstall_result = uninstall_desktop_artifact(
                    installation=installation,
                    artifact_dir=artifact_dir,
                    uninstall_timeout_sec=args.uninstall_timeout_sec,
                )
            except SystemExit as exc:
                status = "failed"
                phase = "uninstall"
                error = str(exc)
                uninstall_result = _build_failed_uninstall_result(
                    installation=installation,
                    artifact_dir=artifact_dir,
                    error=str(exc),
                )

    summary = _build_summary_payload(
        installer_path=installer_path,
        installer_kind=args.installer_kind,
        artifact_dir=artifact_dir,
        workflow_role=args.workflow_role,
        release_ref=args.release_ref,
        resolved_sha=args.resolved_sha,
        distribution_channel=args.distribution_channel,
        status=status,
        phase=phase,
        error=error,
        scenarios=scenarios,
        startup_timeout_sec=args.startup_timeout_sec,
        health_timeout_sec=args.health_timeout_sec,
        restart_limit=args.restart_limit,
        backoff_ms=args.backoff_ms,
        hang_sec=args.hang_sec,
        healthy_startup_timeout_sec=args.healthy_startup_timeout_sec,
        healthy_shutdown_timeout_sec=args.healthy_shutdown_timeout_sec,
        installation=installation,
        healthy_launch_result=healthy_launch_result,
        results=results,
        uninstall_result=uninstall_result,
        started_at_utc=started_at_utc,
    )
    _write_json(artifact_dir / "summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False))
    if status != "passed":
        raise SystemExit(error)


if __name__ == "__main__":
    main()
