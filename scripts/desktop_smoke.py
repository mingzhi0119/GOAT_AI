from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="desktop-smoke",
        description="Boot the desktop Python sidecar and verify the startup handshake.",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=62606)
    parser.add_argument("--timeout-sec", type=float, default=20.0)
    parser.add_argument("--api-key", default="")
    return parser


def build_sidecar_command(*, host: str, port: int, data_root: Path) -> list[str]:
    return [
        sys.executable,
        "-m",
        "goat_ai.desktop_sidecar",
        "--host",
        host,
        "--port",
        str(port),
        "--data-root",
        str(data_root),
        "--log-level",
        "warning",
    ]


def build_request_headers(*, api_key: str = "") -> dict[str, str]:
    headers: dict[str, str] = {}
    if api_key.strip():
        headers["X-GOAT-API-Key"] = api_key.strip()
    return headers


def _request_json(
    url: str,
    *,
    headers: dict[str, str],
    timeout_sec: float = 2.0,
) -> tuple[int, object | None]:
    request = Request(url, headers=headers)
    try:
        with urlopen(request, timeout=timeout_sec) as response:  # noqa: S310
            payload = response.read().decode("utf-8")
            if not payload.strip():
                return response.status, None
            return response.status, json.loads(payload)
    except HTTPError as exc:
        payload = exc.read().decode("utf-8")
        try:
            body: object | None = json.loads(payload) if payload.strip() else None
        except json.JSONDecodeError:
            body = payload or None
        return exc.code, body
    except URLError:
        return 0, None


def wait_for_health(
    *,
    base_url: str,
    headers: dict[str, str],
    timeout_sec: float,
) -> bool:
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        status_code, _ = _request_json(
            f"{base_url}/api/health",
            headers=headers,
        )
        if status_code == 200:
            return True
        time.sleep(0.25)
    return False


def build_failure_diagnostic(
    *,
    base_url: str,
    ready_status: int | None,
    runtime_target: object | None,
) -> str:
    parts = [
        f"Desktop smoke failed: backend never became healthy at {base_url}/api/health.",
        f"Ready status: {ready_status if ready_status is not None else 'unavailable'}.",
    ]
    if runtime_target is not None:
        parts.append(f"Runtime target payload: {runtime_target!r}.")
    parts.append(
        "Check sidecar stderr/stdout and local runtime prerequisites such as Ollama."
    )
    return " ".join(parts)


@dataclass(frozen=True)
class DesktopSmokeResult:
    health_ready: bool
    ready_status: int | None
    runtime_target: object | None


def run_desktop_smoke(
    *,
    host: str,
    port: int,
    timeout_sec: float,
    api_key: str = "",
) -> DesktopSmokeResult:
    base_url = f"http://{host}:{port}"
    headers = build_request_headers(api_key=api_key)

    with tempfile.TemporaryDirectory(prefix="goat-desktop-smoke-") as tmp:
        data_root = Path(tmp) / "data-root"
        process = subprocess.Popen(  # noqa: S603
            build_sidecar_command(host=host, port=port, data_root=data_root),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            health_ready = wait_for_health(
                base_url=base_url,
                headers=headers,
                timeout_sec=timeout_sec,
            )
            ready_status, _ = _request_json(
                f"{base_url}/api/ready",
                headers=headers,
            )
            _, runtime_target = _request_json(
                f"{base_url}/api/system/runtime-target",
                headers=headers,
            )
            return DesktopSmokeResult(
                health_ready=health_ready,
                ready_status=ready_status,
                runtime_target=runtime_target,
            )
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


def main() -> None:
    args = _build_parser().parse_args()
    result = run_desktop_smoke(
        host=args.host,
        port=args.port,
        timeout_sec=args.timeout_sec,
        api_key=args.api_key,
    )
    base_url = f"http://{args.host}:{args.port}"
    if not result.health_ready:
        raise SystemExit(
            build_failure_diagnostic(
                base_url=base_url,
                ready_status=result.ready_status,
                runtime_target=result.runtime_target,
            )
        )
    print(
        json.dumps(
            {
                "health_ready": result.health_ready,
                "ready_status": result.ready_status,
                "runtime_target": result.runtime_target,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
