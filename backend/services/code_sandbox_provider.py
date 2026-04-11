"""Provider abstraction and Docker-backed implementation for code sandbox runs."""

from __future__ import annotations

import contextlib
import hashlib
import os
import time
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from typing import Any, Protocol

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
from goat_ai.feature_gate_reasons import RUNTIME_DOCKER_UNAVAILABLE

_WORKSPACE_DIR = "/workspace"
_OUTPUTS_DIR = "outputs"


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
class SandboxProviderResult:
    """Normalized result returned by an execution provider."""

    provider_name: str
    exit_code: int | None
    stdout: str
    stderr: str
    timed_out: bool
    error_detail: str | None
    output_files: list[dict[str, object]]


class SandboxProvider(Protocol):
    """Execution boundary for one isolated sandbox runtime."""

    provider_name: str

    def run(self, request: SandboxProviderRequest) -> SandboxProviderResult: ...


class DockerSandboxProvider:
    """Execute one sandbox request inside an ephemeral Docker container."""

    provider_name = "docker"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def run(self, request: SandboxProviderRequest) -> SandboxProviderResult:
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
                    wait = self._wait_for_container(container, request.timeout_sec)
                    stdout = self._decode_logs(
                        container.logs(stdout=True, stderr=False)
                    )
                    stderr = self._decode_logs(
                        container.logs(stdout=False, stderr=True)
                    )
                    output_files = self._collect_output_files(workspace)
                    if wait["timed_out"]:
                        return SandboxProviderResult(
                            provider_name=self.provider_name,
                            exit_code=None,
                            stdout=stdout,
                            stderr=stderr,
                            timed_out=True,
                            error_detail="Execution timed out.",
                            output_files=output_files,
                        )
                    exit_code = wait["exit_code"]
                    if exit_code == 0:
                        return SandboxProviderResult(
                            provider_name=self.provider_name,
                            exit_code=0,
                            stdout=stdout,
                            stderr=stderr,
                            timed_out=False,
                            error_detail=None,
                            output_files=output_files,
                        )
                    return SandboxProviderResult(
                        provider_name=self.provider_name,
                        exit_code=exit_code,
                        stdout=stdout,
                        stderr=stderr,
                        timed_out=False,
                        error_detail="Execution exited with a non-zero status.",
                        output_files=output_files,
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

    def _wait_for_container(
        self,
        container: Any,
        timeout_sec: int,
    ) -> dict[str, int | bool | None]:
        deadline = time.monotonic() + timeout_sec
        while time.monotonic() < deadline:
            container.reload()
            state = container.attrs.get("State", {})
            status = str(state.get("Status", ""))
            if status == "exited":
                return {
                    "timed_out": False,
                    "exit_code": int(state.get("ExitCode", 1)),
                }
            if status == "dead":
                return {
                    "timed_out": False,
                    "exit_code": int(state.get("ExitCode", 1)),
                }
            time.sleep(0.1)
        with contextlib.suppress(DockerException):
            container.kill()
        return {"timed_out": True, "exit_code": None}

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

    def _decode_logs(self, raw: bytes) -> str:
        text = raw.decode("utf-8", errors="replace")
        max_bytes = self._settings.code_sandbox_max_output_bytes
        encoded = text.encode("utf-8")
        if len(encoded) <= max_bytes:
            return text
        clipped = encoded[:max_bytes]
        return clipped.decode("utf-8", errors="ignore") + "\n[output truncated]"
