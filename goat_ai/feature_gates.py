"""Pure feature-gate resolution (no FastAPI). See docs/ENGINEERING_STANDARDS.md §15."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from goat_ai.config import Settings, resolve_localhost_sandbox_shell
from goat_ai.feature_gate_reasons import (
    GateKind,
    RUNTIME_DISABLED_BY_OPERATOR,
    RUNTIME_DOCKER_UNAVAILABLE,
    RUNTIME_LOCALHOST_UNAVAILABLE,
    RUNTIME_NOT_IMPLEMENTED,
)

try:
    import docker
    from docker.errors import DockerException
except ImportError:  # pragma: no cover
    docker = None

    class DockerException(Exception):
        """Fallback Docker error when the SDK is unavailable."""


def _sandbox_provider_isolation_level(provider_name: str) -> str:
    if provider_name == "localhost":
        return "host"
    return "container"


def _sandbox_provider_enforces_network_policy(provider_name: str) -> bool:
    return provider_name != "localhost"


@dataclass(frozen=True)
class CodeSandboxFeatureSnapshot:
    """Runtime / dependency readiness for the code-execution sandbox (not AuthZ)."""

    allowed_by_config: bool
    available_on_host: bool
    effective_enabled: bool
    provider_name: str
    isolation_level: str
    network_policy_enforced: bool
    deny_reason: str | None


@dataclass(frozen=True)
class RuntimeFeatureSnapshot:
    """Runtime / dependency readiness for a non-policy-gated optional feature."""

    allowed_by_config: bool
    available_on_host: bool
    effective_enabled: bool
    deny_reason: str | None


def feature_gate_public_detail(
    *, feature_id: str, deny_reason: str, gate_kind: GateKind
) -> str:
    """Stable, client-safe message; internal diagnostics belong in logs only."""
    _ = feature_id
    if gate_kind == "policy":
        return "You are not allowed to use this feature."
    if deny_reason == RUNTIME_DISABLED_BY_OPERATOR:
        return "This feature is disabled on this deployment."
    if deny_reason == RUNTIME_DOCKER_UNAVAILABLE:
        return "This feature is not available because required runtime dependencies are missing or not ready."
    if deny_reason == RUNTIME_LOCALHOST_UNAVAILABLE:
        return "This feature is not available because required runtime dependencies are missing or not ready."
    if deny_reason == RUNTIME_NOT_IMPLEMENTED:
        return "This feature has not been implemented on this deployment yet."
    return "This feature is not available on this deployment."


def _docker_paths_to_probe(settings: Settings) -> list[Path]:
    raw = settings.docker_socket_path.strip()
    if raw:
        return [Path(raw)]
    if os.name == "nt":
        return [Path(r"\\.\pipe\docker_engine")]
    return [Path("/var/run/docker.sock")]


def _docker_base_url_from_settings(settings: Settings) -> str:
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


def _path_usable_for_docker(path: Path) -> bool:
    """Best-effort probe: Unix `docker.sock` or Windows Docker Engine named pipe."""
    try:
        if os.name == "nt":
            ps = str(path).lower()
            return "pipe" in ps and path.exists()
        return path.is_socket()
    except OSError:
        return False


def probe_docker_available(settings: Settings) -> bool:
    """Return True if a configured or default Docker socket/pipe appears usable."""
    if docker is None:
        return False
    if not any(_path_usable_for_docker(candidate) for candidate in _docker_paths_to_probe(settings)):
        return False
    client = None
    try:
        client = docker.DockerClient(
            base_url=_docker_base_url_from_settings(settings),
            timeout=1,
        )
        return bool(client.ping())
    except DockerException:
        return False
    finally:
        if client is not None:
            try:
                client.close()
            except DockerException:
                pass


def probe_localhost_sandbox_available(settings: Settings) -> bool:
    """Return True when a usable local shell exists for the localhost provider."""
    return resolve_localhost_sandbox_shell(settings) is not None


def compute_code_sandbox_snapshot(settings: Settings) -> CodeSandboxFeatureSnapshot:
    """Combine operator intent (config) with host probe for effective enablement."""
    allowed = settings.feature_code_sandbox_enabled
    provider_name = settings.code_sandbox_provider
    isolation_level = _sandbox_provider_isolation_level(provider_name)
    network_policy_enforced = _sandbox_provider_enforces_network_policy(provider_name)
    if not allowed:
        return CodeSandboxFeatureSnapshot(
            allowed_by_config=False,
            available_on_host=False,
            effective_enabled=False,
            provider_name=provider_name,
            isolation_level=isolation_level,
            network_policy_enforced=network_policy_enforced,
            deny_reason=RUNTIME_DISABLED_BY_OPERATOR,
        )
    if provider_name == "localhost":
        on_host = probe_localhost_sandbox_available(settings)
        deny_reason = RUNTIME_LOCALHOST_UNAVAILABLE
    else:
        on_host = probe_docker_available(settings)
        deny_reason = RUNTIME_DOCKER_UNAVAILABLE
    if not on_host:
        return CodeSandboxFeatureSnapshot(
            allowed_by_config=True,
            available_on_host=False,
            effective_enabled=False,
            provider_name=provider_name,
            isolation_level=isolation_level,
            network_policy_enforced=network_policy_enforced,
            deny_reason=deny_reason,
        )
    return CodeSandboxFeatureSnapshot(
        allowed_by_config=True,
        available_on_host=True,
        effective_enabled=True,
        provider_name=provider_name,
        isolation_level=isolation_level,
        network_policy_enforced=network_policy_enforced,
        deny_reason=None,
    )


def compute_agent_workbench_snapshot(settings: Settings) -> RuntimeFeatureSnapshot:
    """Resolve the shared workbench runtime envelope for future agent surfaces."""
    if not settings.feature_agent_workbench_enabled:
        return RuntimeFeatureSnapshot(
            allowed_by_config=False,
            available_on_host=False,
            effective_enabled=False,
            deny_reason=RUNTIME_DISABLED_BY_OPERATOR,
        )
    return RuntimeFeatureSnapshot(
        allowed_by_config=True,
        available_on_host=True,
        effective_enabled=True,
        deny_reason=None,
    )
