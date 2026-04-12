"""Provider abstraction and Docker-backed implementation for code sandbox runs."""

from __future__ import annotations

import contextlib
import hashlib
import os
import queue
import shutil
import subprocess
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from typing import Any, Generator, Literal, Protocol

try:
    import docker
    from docker.errors import DockerException, NotFound
except ImportError:  # pragma: no cover - exercised in environments without docker SDK
    docker = SimpleNamespace(DockerClient=None, from_env=None)

    class DockerException(Exception):
        """Fallback Docker SDK error when the dependency is unavailable."""

    class NotFound(DockerException):
        """Fallback not-found error when the dependency is unavailable."""


from backend.services.exceptions import FeatureNotAvailable
from backend.types import Settings
from goat_ai.config.feature_gate_reasons import (
    RUNTIME_DOCKER_UNAVAILABLE,
    RUNTIME_LOCALHOST_UNAVAILABLE,
)

_WORKSPACE_DIR = "/workspace"
_OUTPUTS_DIR = "outputs"
_STREAM_DONE = "__done__"
_STREAM_ERROR = "__error__"
SandboxIsolationLevel = Literal["container", "host"]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def docker_base_url_from_settings(settings: Settings) -> str | None:
    raw = settings.docker_socket_path.strip()
    if not raw:
        if os.name == "nt":
            return "npipe:////./pipe/docker_engine"
        return "unix:///var/run/docker.sock"
    lowered = raw.lower()
    if lowered.startswith(("unix://", "npipe://", "tcp://", "http://", "https://")):
        return raw
    if os.name == "nt" or "pipe" in lowered:
        normalized = raw.replace("\\", "/").lstrip("/")
        return f"npipe:////{normalized}"
    if raw.startswith("/"):
        return f"unix://{raw}"
    return raw


@dataclass(frozen=True, kw_only=True)
class SandboxProviderRequest:
    """Normalized request handed to an execution provider."""

    execution_id: str
    runtime_preset: str
    code: str | None
    command: str | None
    stdin: str | None
    inline_files: list[dict[str, str]]
    timeout_sec: int
    network_policy: str


@dataclass(frozen=True, kw_only=True)
class SandboxProviderLogChunk:
    """One streamed stdout/stderr chunk emitted while the provider runs."""

    stream_name: Literal["stdout", "stderr"]
    created_at: str
    text: str


@dataclass(frozen=True, kw_only=True)
class SandboxProviderResult:
    """Normalized terminal result returned by an execution provider."""

    provider_name: str
    exit_code: int | None
    stdout: str
    stderr: str
    timed_out: bool
    error_detail: str | None
    output_files: list[dict[str, object]]


SandboxProviderEvent = SandboxProviderLogChunk | SandboxProviderResult


class SandboxProvider(Protocol):
    """Execution boundary for one isolated sandbox runtime."""

    provider_name: str
    isolation_level: SandboxIsolationLevel
    network_policy_enforced: bool

    def run_stream(
        self,
        request: SandboxProviderRequest,
    ) -> Generator[SandboxProviderEvent, None, None]: ...


def sandbox_provider_isolation_level(provider_name: str) -> SandboxIsolationLevel:
    if provider_name == "localhost":
        return "host"
    return "container"


def sandbox_provider_enforces_network_policy(provider_name: str) -> bool:
    return provider_name != "localhost"


class DockerSandboxProvider:
    """Execute one sandbox request inside an ephemeral Docker container."""

    provider_name = "docker"
    isolation_level: SandboxIsolationLevel = "container"
    network_policy_enforced = True

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def run_stream(
        self,
        request: SandboxProviderRequest,
    ) -> Generator[SandboxProviderEvent, None, None]:
        try:
            if docker.DockerClient is None:
                raise FeatureNotAvailable(
                    feature_id="code_sandbox",
                    deny_reason=RUNTIME_DOCKER_UNAVAILABLE,
                    gate_kind="runtime",
                )
            base_url = docker_base_url_from_settings(self._settings)
            client = (
                docker.DockerClient(base_url=base_url)
                if base_url
                else docker.from_env()
            )
            container = None
            with TemporaryDirectory(prefix="goat-sandbox-") as tmp:
                workspace = Path(tmp)
                self._seed_workspace(workspace=workspace, request=request)
                command = self._build_container_command(request)
                try:
                    container = client.containers.create(
                        image=self._settings.code_sandbox_default_image,
                        command=command,
                        working_dir=_WORKSPACE_DIR,
                        detach=True,
                        network_disabled=request.network_policy == "disabled",
                        mem_limit=f"{self._settings.code_sandbox_memory_mb}m",
                        nano_cpus=int(
                            self._settings.code_sandbox_cpu_limit * 1_000_000_000
                        ),
                        volumes={
                            str(workspace): {"bind": _WORKSPACE_DIR, "mode": "rw"}
                        },
                        auto_remove=False,
                    )
                    container.start()
                    yield from self._stream_container_run(
                        container=container,
                        workspace=workspace,
                        timeout_sec=request.timeout_sec,
                    )
                finally:
                    with contextlib.suppress(NotFound, DockerException, OSError):
                        if container is not None:
                            container.remove(force=True)
                    with contextlib.suppress(DockerException):
                        client.close()
        except DockerException as exc:
            raise FeatureNotAvailable(
                feature_id="code_sandbox",
                deny_reason=RUNTIME_DOCKER_UNAVAILABLE,
                gate_kind="runtime",
            ) from exc

    def _stream_container_run(
        self,
        *,
        container: Any,
        workspace: Path,
        timeout_sec: int,
    ) -> Generator[SandboxProviderEvent, None, None]:
        log_queue: queue.Queue[tuple[str, bytes | None]] = queue.Queue()
        finished = threading.Event()

        def pump_logs() -> None:
            try:
                stream = container.attach(
                    stream=True,
                    stdout=True,
                    stderr=True,
                    logs=True,
                    demux=True,
                )
                for payload in stream:
                    if payload is None:
                        continue
                    if isinstance(payload, tuple):
                        stdout_chunk, stderr_chunk = payload
                    else:
                        stdout_chunk, stderr_chunk = payload, None
                    if stdout_chunk:
                        log_queue.put(("stdout", stdout_chunk))
                    if stderr_chunk:
                        log_queue.put(("stderr", stderr_chunk))
            except DockerException as exc:  # pragma: no cover - rare runtime path
                log_queue.put(
                    (_STREAM_ERROR, str(exc).encode("utf-8", errors="ignore"))
                )
            finally:
                finished.set()
                log_queue.put((_STREAM_DONE, None))

        thread = threading.Thread(target=pump_logs, daemon=True)
        thread.start()

        deadline = time.monotonic() + timeout_sec
        timed_out = False
        exit_code: int | None = None
        provider_error: str | None = None

        try:
            while True:
                for event in self._drain_log_queue(log_queue):
                    stream_name, raw = event
                    if stream_name == _STREAM_ERROR:
                        provider_error = self._decode_text(raw or b"")
                        continue
                    if stream_name == _STREAM_DONE:
                        continue
                    text = self._decode_text(raw or b"")
                    if text:
                        yield SandboxProviderLogChunk(
                            stream_name=stream_name, created_at=_utc_now(), text=text
                        )

                container.reload()
                state = container.attrs.get("State", {})
                status = str(state.get("Status", ""))
                if status in {"exited", "dead"}:
                    exit_code = int(state.get("ExitCode", 1))
                    break
                if time.monotonic() >= deadline:
                    timed_out = True
                    with contextlib.suppress(DockerException):
                        container.kill()
                    break
                time.sleep(0.1)

            thread.join(timeout=1.0)
            for event in self._drain_log_queue(log_queue):
                stream_name, raw = event
                if stream_name == _STREAM_ERROR:
                    provider_error = self._decode_text(raw or b"")
                    continue
                if stream_name == _STREAM_DONE:
                    continue
                text = self._decode_text(raw or b"")
                if text:
                    yield SandboxProviderLogChunk(
                        stream_name=stream_name, created_at=_utc_now(), text=text
                    )

            output_files = self._collect_output_files(workspace)
            if timed_out:
                yield SandboxProviderResult(
                    provider_name=self.provider_name,
                    exit_code=None,
                    stdout="",
                    stderr="",
                    timed_out=True,
                    error_detail="Execution timed out.",
                    output_files=output_files,
                )
                return
            if provider_error:
                yield SandboxProviderResult(
                    provider_name=self.provider_name,
                    exit_code=exit_code,
                    stdout="",
                    stderr="",
                    timed_out=False,
                    error_detail="Failed to stream sandbox logs.",
                    output_files=output_files,
                )
                return
            if exit_code == 0:
                yield SandboxProviderResult(
                    provider_name=self.provider_name,
                    exit_code=0,
                    stdout="",
                    stderr="",
                    timed_out=False,
                    error_detail=None,
                    output_files=output_files,
                )
                return
            yield SandboxProviderResult(
                provider_name=self.provider_name,
                exit_code=exit_code,
                stdout="",
                stderr="",
                timed_out=False,
                error_detail="Execution exited with a non-zero status.",
                output_files=output_files,
            )
        finally:
            if not finished.is_set():
                finished.set()

    def _drain_log_queue(
        self, log_queue: queue.Queue[tuple[str, bytes | None]]
    ) -> list[tuple[str, bytes | None]]:
        events: list[tuple[str, bytes | None]] = []
        while True:
            try:
                events.append(log_queue.get_nowait())
            except queue.Empty:
                return events

    def _build_container_command(self, request: SandboxProviderRequest) -> list[str]:
        if request.command:
            entry = request.command
        else:
            entry = "/bin/sh ./snippet.sh"
        if request.stdin:
            entry = f"{entry} < .goat_stdin.txt"
        return ["/bin/sh", "-lc", entry]

    def _seed_workspace(
        self,
        *,
        workspace: Path,
        request: SandboxProviderRequest,
    ) -> None:
        (workspace / _OUTPUTS_DIR).mkdir(parents=True, exist_ok=True)
        if request.code is not None:
            script_path = workspace / "snippet.sh"
            script_path.write_text(request.code, encoding="utf-8")
        if request.stdin is not None:
            (workspace / ".goat_stdin.txt").write_text(request.stdin, encoding="utf-8")
        for item in request.inline_files:
            rel = Path(item["filename"])
            full = workspace / rel
            full.parent.mkdir(parents=True, exist_ok=True)
            full.write_text(item["content"], encoding="utf-8")

    def _collect_output_files(self, workspace: Path) -> list[dict[str, object]]:
        outputs_root = workspace / _OUTPUTS_DIR
        if not outputs_root.is_dir():
            return []
        out: list[dict[str, object]] = []
        for path in sorted(outputs_root.rglob("*")):
            if not path.is_file():
                continue
            rel = path.relative_to(outputs_root).as_posix()
            out.append(
                {
                    "path": rel,
                    "byte_size": path.stat().st_size,
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                }
            )
        return out

    def _decode_text(self, raw: bytes) -> str:
        return raw.decode("utf-8", errors="replace")


def _resolve_localhost_shell(settings: Settings) -> str | None:
    configured = settings.code_sandbox_localhost_shell.strip()
    if configured:
        return shutil.which(configured) or (
            configured if Path(configured).is_file() else None
        )
    if os.name == "nt":
        return shutil.which("pwsh.exe") or shutil.which("powershell.exe")
    return shutil.which("sh") or ("/bin/sh" if Path("/bin/sh").is_file() else None)


class LocalHostProvider:
    """Execute one sandbox request directly on the host shell as a dev fallback."""

    provider_name = "localhost"
    isolation_level: SandboxIsolationLevel = "host"
    network_policy_enforced = False

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def run_stream(
        self,
        request: SandboxProviderRequest,
    ) -> Generator[SandboxProviderEvent, None, None]:
        shell = _resolve_localhost_shell(self._settings)
        if shell is None:
            raise FeatureNotAvailable(
                feature_id="code_sandbox",
                deny_reason=RUNTIME_LOCALHOST_UNAVAILABLE,
                gate_kind="runtime",
            )

        with TemporaryDirectory(prefix="goat-sandbox-local-") as tmp:
            workspace = Path(tmp)
            self._seed_workspace(workspace=workspace, request=request)
            command = self._build_host_command(shell=shell, request=request)
            creationflags = (
                getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
            )
            try:
                process = subprocess.Popen(
                    command,
                    cwd=workspace,
                    stdin=subprocess.PIPE
                    if request.stdin is not None
                    else subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    bufsize=0,
                    creationflags=creationflags,
                )
            except OSError as exc:
                raise FeatureNotAvailable(
                    feature_id="code_sandbox",
                    deny_reason=RUNTIME_LOCALHOST_UNAVAILABLE,
                    gate_kind="runtime",
                ) from exc

            try:
                if request.stdin is not None and process.stdin is not None:
                    process.stdin.write(request.stdin.encode("utf-8"))
                    process.stdin.close()
                yield from self._stream_host_run(
                    process=process,
                    workspace=workspace,
                    timeout_sec=request.timeout_sec,
                )
            finally:
                with contextlib.suppress(OSError):
                    if process.poll() is None:
                        process.kill()
                with contextlib.suppress(OSError):
                    if process.stdout is not None:
                        process.stdout.close()
                with contextlib.suppress(OSError):
                    if process.stderr is not None:
                        process.stderr.close()
                with contextlib.suppress(OSError):
                    if process.stdin is not None and not process.stdin.closed:
                        process.stdin.close()

    def _build_host_command(
        self,
        *,
        shell: str,
        request: SandboxProviderRequest,
    ) -> list[str]:
        if os.name == "nt":
            if request.command:
                return [
                    shell,
                    "-NoLogo",
                    "-NoProfile",
                    "-NonInteractive",
                    "-Command",
                    request.command,
                ]
            return [
                shell,
                "-NoLogo",
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                "snippet.ps1",
            ]
        if request.command:
            return [shell, "-lc", request.command]
        return [shell, "snippet.sh"]

    def _stream_host_run(
        self,
        *,
        process: subprocess.Popen[bytes],
        workspace: Path,
        timeout_sec: int,
    ) -> Generator[SandboxProviderEvent, None, None]:
        log_queue: queue.Queue[tuple[str, bytes | None]] = queue.Queue()
        finished = threading.Event()
        remaining = 2
        lock = threading.Lock()

        def pump_stream(stream_name: Literal["stdout", "stderr"], stream: Any) -> None:
            nonlocal remaining
            try:
                while True:
                    chunk = stream.read(1024)
                    if not chunk:
                        break
                    log_queue.put((stream_name, chunk))
            except OSError as exc:
                log_queue.put(
                    (_STREAM_ERROR, str(exc).encode("utf-8", errors="ignore"))
                )
            finally:
                with lock:
                    remaining -= 1
                    if remaining == 0:
                        finished.set()
                        log_queue.put((_STREAM_DONE, None))

        stdout_thread = threading.Thread(
            target=pump_stream,
            args=("stdout", process.stdout),
            daemon=True,
        )
        stderr_thread = threading.Thread(
            target=pump_stream,
            args=("stderr", process.stderr),
            daemon=True,
        )
        stdout_thread.start()
        stderr_thread.start()

        deadline = time.monotonic() + timeout_sec
        timed_out = False
        exit_code: int | None = None
        provider_error: str | None = None

        try:
            while True:
                for event in self._drain_log_queue(log_queue):
                    stream_name, raw = event
                    if stream_name == _STREAM_ERROR:
                        provider_error = self._decode_text(raw or b"")
                        continue
                    if stream_name == _STREAM_DONE:
                        continue
                    text = self._decode_text(raw or b"")
                    if text:
                        yield SandboxProviderLogChunk(
                            stream_name=stream_name, created_at=_utc_now(), text=text
                        )

                exit_code = process.poll()
                if exit_code is not None and finished.is_set():
                    break
                if time.monotonic() >= deadline:
                    timed_out = True
                    with contextlib.suppress(OSError):
                        process.kill()
                    break
                time.sleep(0.05)

            with contextlib.suppress(OSError, subprocess.TimeoutExpired):
                process.wait(timeout=1.0)
            stdout_thread.join(timeout=1.0)
            stderr_thread.join(timeout=1.0)
            for event in self._drain_log_queue(log_queue):
                stream_name, raw = event
                if stream_name == _STREAM_ERROR:
                    provider_error = self._decode_text(raw or b"")
                    continue
                if stream_name == _STREAM_DONE:
                    continue
                text = self._decode_text(raw or b"")
                if text:
                    yield SandboxProviderLogChunk(
                        stream_name=stream_name, created_at=_utc_now(), text=text
                    )

            output_files = self._collect_output_files(workspace)
            if timed_out:
                yield SandboxProviderResult(
                    provider_name=self.provider_name,
                    exit_code=None,
                    stdout="",
                    stderr="",
                    timed_out=True,
                    error_detail="Execution timed out.",
                    output_files=output_files,
                )
                return
            if provider_error:
                yield SandboxProviderResult(
                    provider_name=self.provider_name,
                    exit_code=exit_code,
                    stdout="",
                    stderr="",
                    timed_out=False,
                    error_detail="Failed to stream sandbox logs.",
                    output_files=output_files,
                )
                return
            if exit_code == 0:
                yield SandboxProviderResult(
                    provider_name=self.provider_name,
                    exit_code=0,
                    stdout="",
                    stderr="",
                    timed_out=False,
                    error_detail=None,
                    output_files=output_files,
                )
                return
            yield SandboxProviderResult(
                provider_name=self.provider_name,
                exit_code=exit_code,
                stdout="",
                stderr="",
                timed_out=False,
                error_detail="Execution exited with a non-zero status.",
                output_files=output_files,
            )
        finally:
            if not finished.is_set():
                finished.set()

    def _drain_log_queue(
        self, log_queue: queue.Queue[tuple[str, bytes | None]]
    ) -> list[tuple[str, bytes | None]]:
        events: list[tuple[str, bytes | None]] = []
        while True:
            try:
                events.append(log_queue.get_nowait())
            except queue.Empty:
                return events

    def _seed_workspace(
        self,
        *,
        workspace: Path,
        request: SandboxProviderRequest,
    ) -> None:
        (workspace / _OUTPUTS_DIR).mkdir(parents=True, exist_ok=True)
        if request.code is not None:
            (workspace / "snippet.sh").write_text(request.code, encoding="utf-8")
            (workspace / "snippet.ps1").write_text(request.code, encoding="utf-8")
        for item in request.inline_files:
            rel = Path(item["filename"])
            full = workspace / rel
            full.parent.mkdir(parents=True, exist_ok=True)
            full.write_text(item["content"], encoding="utf-8")

    def _collect_output_files(self, workspace: Path) -> list[dict[str, object]]:
        outputs_root = workspace / _OUTPUTS_DIR
        if not outputs_root.is_dir():
            return []
        out: list[dict[str, object]] = []
        for path in sorted(outputs_root.rglob("*")):
            if not path.is_file():
                continue
            rel = path.relative_to(outputs_root).as_posix()
            out.append(
                {
                    "path": rel,
                    "byte_size": path.stat().st_size,
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                }
            )
        return out

    def _decode_text(self, raw: bytes) -> str:
        return raw.decode("utf-8", errors="replace")
