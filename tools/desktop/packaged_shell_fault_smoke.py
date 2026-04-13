from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import time
from contextlib import contextmanager, nullcontext
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

SCENARIO_EXPECTED_STAGE = {
    "missing_sidecar": "backend_spawn_failed",
    "exit_before_ready": "backend_terminated_before_ready",
    "hang_before_ready": "health_wait_timeout",
}

SCENARIO_EQUIVALENT_LOG_MARKERS = {
    "exit_before_ready": (
        "GOAT desktop backend sidecar terminated before startup completed",
    ),
}

INTERNAL_TEST_FLAG = "GOAT_DESKTOP_INTERNAL_TEST"
INTERNAL_TEST_SCENARIO = "GOAT_DESKTOP_INTERNAL_TEST_SCENARIO"
INTERNAL_TEST_HEALTH_TIMEOUT_SEC = "GOAT_DESKTOP_INTERNAL_TEST_HEALTH_TIMEOUT_SEC"
INTERNAL_TEST_RESTART_LIMIT = "GOAT_DESKTOP_INTERNAL_TEST_PRE_READY_RESTART_LIMIT"
INTERNAL_TEST_BACKOFF_MS = "GOAT_DESKTOP_INTERNAL_TEST_PRE_READY_BACKOFF_MS"
INTERNAL_TEST_HANG_SEC = "GOAT_DESKTOP_INTERNAL_TEST_HANG_SEC"
DEFAULT_WINDOWS_APP_IDENTIFIER = "com.simonbb.goatai"


@dataclass(frozen=True)
class PackagedShellFaultResult:
    scenario: str
    stdout_path: str
    stderr_path: str
    exit_code: int | None = None
    failure_stage: str | None = None
    log_path: str | None = None
    status: str = "passed"
    error: str | None = None
    started_at_utc: str | None = None
    completed_at_utc: str | None = None


class PackagedShellFaultScenarioError(SystemExit):
    def __init__(
        self,
        message: str,
        *,
        result: PackagedShellFaultResult,
    ) -> None:
        super().__init__(message)
        self.result = result


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="packaged-shell-fault-smoke",
        description=(
            "Run fault-injected packaged desktop startup scenarios and assert "
            "that pre-ready failures stay fail-closed with bounded retry evidence."
        ),
    )
    parser.add_argument("--desktop-exe", type=Path, required=True)
    parser.add_argument("--sidecar", type=Path, required=True)
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument(
        "--scenario",
        action="append",
        choices=sorted(SCENARIO_EXPECTED_STAGE),
        dest="scenarios",
    )
    parser.add_argument("--startup-timeout-sec", type=float, default=15.0)
    parser.add_argument("--health-timeout-sec", type=int, default=2)
    parser.add_argument("--restart-limit", type=int, default=1)
    parser.add_argument("--backoff-ms", type=int, default=100)
    parser.add_argument("--hang-sec", type=float, default=5.0)
    parser.add_argument("--app-identifier", default=DEFAULT_WINDOWS_APP_IDENTIFIER)
    return parser


def utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _reserve_local_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def build_fault_smoke_environment(
    *,
    base_dir: Path,
    scenario: str,
    health_timeout_sec: int,
    restart_limit: int,
    backoff_ms: int,
    hang_sec: float,
    app_identifier: str = DEFAULT_WINDOWS_APP_IDENTIFIER,
) -> dict[str, str]:
    runtime_root = base_dir / "runtime-env"
    local_appdata = runtime_root / "LocalAppData"
    roaming_appdata = runtime_root / "RoamingAppData"
    local_appdata.mkdir(parents=True, exist_ok=True)
    roaming_appdata.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env["LOCALAPPDATA"] = str(local_appdata)
    env["APPDATA"] = str(roaming_appdata)
    env["GOAT_DESKTOP_BACKEND_HOST"] = "127.0.0.1"
    env["GOAT_DESKTOP_BACKEND_PORT"] = str(_reserve_local_port())
    env["GOAT_DESKTOP_APP_DATA_DIR"] = str(local_appdata / app_identifier)
    env["GOAT_RUNTIME_ROOT"] = env["GOAT_DESKTOP_APP_DATA_DIR"]
    env["GOAT_LOG_DIR"] = str(local_appdata / app_identifier / "logs")
    env["GOAT_LOG_PATH"] = str(local_appdata / app_identifier / "chat_logs.db")
    env["GOAT_DATA_DIR"] = str(local_appdata / app_identifier / "data")
    env["GOAT_DESKTOP_SHELL_LOG_PATH"] = str(
        local_appdata / app_identifier / "logs" / "desktop-shell.log"
    )
    env[INTERNAL_TEST_FLAG] = "1"
    env[INTERNAL_TEST_SCENARIO] = "" if scenario == "missing_sidecar" else scenario
    env[INTERNAL_TEST_HEALTH_TIMEOUT_SEC] = str(health_timeout_sec)
    env[INTERNAL_TEST_RESTART_LIMIT] = str(restart_limit)
    env[INTERNAL_TEST_BACKOFF_MS] = str(backoff_ms)
    env[INTERNAL_TEST_HANG_SEC] = str(hang_sec)
    return env


def discover_desktop_log(root: Path) -> Path:
    matches = [path for path in root.rglob("desktop-shell.log") if path.is_file()]
    if not matches:
        raise SystemExit(f"Could not find desktop-shell.log under {root}.")
    return max(matches, key=lambda path: path.stat().st_mtime_ns)


def fallback_desktop_log_path(
    app_identifier: str,
    *,
    local_appdata: Path | None = None,
) -> Path:
    local_appdata = (
        local_appdata
        if local_appdata is not None
        else Path(os.environ.get("LOCALAPPDATA", "")).expanduser()
    )
    if not str(local_appdata).strip():
        raise SystemExit(
            "LOCALAPPDATA was not available for packaged-shell fault smoke."
        )
    return local_appdata / app_identifier / "logs" / "desktop-shell.log"


def extract_log_delta(log_path: Path, baseline: bytes) -> bytes:
    current = log_path.read_bytes()
    if baseline and current.startswith(baseline):
        return current[len(baseline) :]
    return current


def validate_fault_smoke_log(*, scenario: str, exit_code: int, log_text: str) -> str:
    if exit_code == 0:
        raise SystemExit(
            f"Scenario {scenario} unexpectedly exited cleanly; expected fail-closed behavior."
        )
    expected_stage = SCENARIO_EXPECTED_STAGE[scenario]
    equivalent_markers = SCENARIO_EQUIVALENT_LOG_MARKERS.get(scenario, ())
    if expected_stage not in log_text and not any(
        marker in log_text for marker in equivalent_markers
    ):
        raise SystemExit(
            f"Scenario {scenario} did not record expected failure stage {expected_stage!r}."
        )
    if "Retrying before window reveal after" not in log_text:
        raise SystemExit(
            f"Scenario {scenario} did not record bounded retry/backoff evidence."
        )
    return expected_stage


def _launch_desktop(
    *,
    desktop_exe: Path,
    env: dict[str, str],
    stdout_path: Path,
    stderr_path: Path,
    timeout_sec: float,
) -> int:
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    with (
        stdout_path.open("w", encoding="utf-8") as stdout_file,
        stderr_path.open("w", encoding="utf-8") as stderr_file,
    ):
        process = subprocess.Popen(  # noqa: S603
            [str(desktop_exe)],
            cwd=str(desktop_exe.parent),
            env=env,
            stdout=stdout_file,
            stderr=stderr_file,
            creationflags=creationflags,
        )
        try:
            returncode = process.wait(timeout=timeout_sec)
        except subprocess.TimeoutExpired as exc:
            process.kill()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                pass
            raise SystemExit(
                f"Desktop process did not exit within {timeout_sec} seconds."
            ) from exc
    return int(returncode)


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )


def _write_scenario_result(
    *,
    scenario_dir: Path,
    result: PackagedShellFaultResult,
) -> None:
    _write_json(scenario_dir / "result.json", asdict(result))


def _build_failed_result(
    *,
    scenario: str,
    scenario_dir: Path,
    stdout_path: Path,
    stderr_path: Path,
    started_at_utc: str,
    error: str,
    log_path: Path | None = None,
    exit_code: int | None = None,
    failure_stage: str | None = None,
) -> PackagedShellFaultResult:
    return PackagedShellFaultResult(
        scenario=scenario,
        stdout_path=str(stdout_path),
        stderr_path=str(stderr_path),
        exit_code=exit_code,
        failure_stage=failure_stage,
        log_path=str(log_path) if log_path is not None else None,
        status="failed",
        error=error,
        started_at_utc=started_at_utc,
        completed_at_utc=utc_now(),
    )


@contextmanager
def _temporarily_move_sidecar(sidecar_path: Path, scenario_dir: Path):
    if not sidecar_path.is_file():
        raise SystemExit(f"Expected packaged sidecar at {sidecar_path}.")
    backup_path = scenario_dir / sidecar_path.name
    sidecar_path.replace(backup_path)
    try:
        yield
    finally:
        if backup_path.exists():
            backup_path.replace(sidecar_path)


def run_fault_scenario(
    *,
    desktop_exe: Path,
    sidecar_path: Path,
    artifact_dir: Path,
    scenario: str,
    startup_timeout_sec: float,
    health_timeout_sec: int,
    restart_limit: int,
    backoff_ms: int,
    hang_sec: float,
    app_identifier: str,
) -> PackagedShellFaultResult:
    scenario_dir = artifact_dir / scenario
    scenario_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = scenario_dir / "desktop.stdout.log"
    stderr_path = scenario_dir / "desktop.stderr.log"
    started_at_utc = utc_now()
    env = build_fault_smoke_environment(
        base_dir=scenario_dir,
        scenario=scenario,
        health_timeout_sec=health_timeout_sec,
        restart_limit=restart_limit,
        backoff_ms=backoff_ms,
        hang_sec=hang_sec,
        app_identifier=app_identifier,
    )
    fallback_log = fallback_desktop_log_path(
        app_identifier,
        local_appdata=Path(env["LOCALAPPDATA"]),
    )
    baseline_log = fallback_log.read_bytes() if fallback_log.is_file() else b""
    sidecar_context = (
        _temporarily_move_sidecar(sidecar_path, scenario_dir)
        if scenario == "missing_sidecar"
        else nullcontext()
    )

    try:
        with sidecar_context:
            exit_code = _launch_desktop(
                desktop_exe=desktop_exe,
                env=env,
                stdout_path=stdout_path,
                stderr_path=stderr_path,
                timeout_sec=startup_timeout_sec,
            )

        time.sleep(0.5)
        if any(path.is_file() for path in scenario_dir.rglob("desktop-shell.log")):
            source_log_path = discover_desktop_log(scenario_dir)
            copied_log_path = source_log_path
            log_text = source_log_path.read_text(encoding="utf-8")
        elif fallback_log.is_file():
            copied_log_path = scenario_dir / "desktop-shell.log"
            copied_log_path.write_bytes(extract_log_delta(fallback_log, baseline_log))
            log_text = copied_log_path.read_text(encoding="utf-8", errors="replace")
        else:
            raise SystemExit(
                f"Could not find desktop-shell.log under {scenario_dir} or at {fallback_log}."
            )
        failure_stage = validate_fault_smoke_log(
            scenario=scenario,
            exit_code=exit_code,
            log_text=log_text,
        )
        result = PackagedShellFaultResult(
            scenario=scenario,
            stdout_path=str(stdout_path),
            stderr_path=str(stderr_path),
            exit_code=exit_code,
            failure_stage=failure_stage,
            log_path=str(copied_log_path),
            started_at_utc=started_at_utc,
            completed_at_utc=utc_now(),
        )
        _write_scenario_result(scenario_dir=scenario_dir, result=result)
        return result
    except SystemExit as exc:
        failed_result = _build_failed_result(
            scenario=scenario,
            scenario_dir=scenario_dir,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            started_at_utc=started_at_utc,
            error=str(exc),
            log_path=(
                scenario_dir / "desktop-shell.log"
                if (scenario_dir / "desktop-shell.log").is_file()
                else None
            ),
        )
        _write_scenario_result(scenario_dir=scenario_dir, result=failed_result)
        raise PackagedShellFaultScenarioError(
            str(exc),
            result=failed_result,
        ) from exc


def _build_summary_payload(
    *,
    status: str,
    phase: str,
    error: str | None,
    desktop_exe: Path,
    sidecar_path: Path,
    artifact_dir: Path,
    scenarios: list[str],
    startup_timeout_sec: float,
    health_timeout_sec: int,
    restart_limit: int,
    backoff_ms: int,
    hang_sec: float,
    app_identifier: str,
    results: list[PackagedShellFaultResult],
    started_at_utc: str,
) -> dict[str, object]:
    return {
        "status": status,
        "phase": phase,
        "error": error,
        "started_at_utc": started_at_utc,
        "completed_at_utc": utc_now(),
        "artifact_dir": str(artifact_dir),
        "desktop_exe": str(desktop_exe),
        "sidecar_path": str(sidecar_path),
        "config": {
            "scenarios": scenarios,
            "startup_timeout_sec": startup_timeout_sec,
            "health_timeout_sec": health_timeout_sec,
            "restart_limit": restart_limit,
            "backoff_ms": backoff_ms,
            "hang_sec": hang_sec,
            "app_identifier": app_identifier,
        },
        "results": [asdict(result) for result in results],
    }


def main() -> None:
    args = _build_parser().parse_args()
    desktop_exe = args.desktop_exe.resolve()
    sidecar_path = args.sidecar.resolve()
    artifact_dir = args.artifact_dir.resolve()
    artifact_dir.mkdir(parents=True, exist_ok=True)
    scenarios = args.scenarios or list(SCENARIO_EXPECTED_STAGE)
    started_at_utc = utc_now()
    results: list[PackagedShellFaultResult] = []
    status = "passed"
    phase = "completed"
    error: str | None = None

    for scenario in scenarios:
        try:
            result = run_fault_scenario(
                desktop_exe=desktop_exe,
                sidecar_path=sidecar_path,
                artifact_dir=artifact_dir,
                scenario=scenario,
                startup_timeout_sec=args.startup_timeout_sec,
                health_timeout_sec=args.health_timeout_sec,
                restart_limit=args.restart_limit,
                backoff_ms=args.backoff_ms,
                hang_sec=args.hang_sec,
                app_identifier=args.app_identifier,
            )
            results.append(result)
        except PackagedShellFaultScenarioError as exc:
            status = "failed"
            phase = f"scenario:{scenario}"
            error = str(exc)
            results.append(exc.result)
            break

    summary = _build_summary_payload(
        status=status,
        phase=phase,
        error=error,
        desktop_exe=desktop_exe,
        sidecar_path=sidecar_path,
        artifact_dir=artifact_dir,
        scenarios=scenarios,
        startup_timeout_sec=args.startup_timeout_sec,
        health_timeout_sec=args.health_timeout_sec,
        restart_limit=args.restart_limit,
        backoff_ms=args.backoff_ms,
        hang_sec=args.hang_sec,
        app_identifier=args.app_identifier,
        results=results,
        started_at_utc=started_at_utc,
    )
    _write_json(artifact_dir / "summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False))
    if status != "passed":
        raise SystemExit(error)


if __name__ == "__main__":
    main()
