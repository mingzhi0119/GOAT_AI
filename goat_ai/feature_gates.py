"""Pure feature-gate resolution (no FastAPI). See docs/ENGINEERING_STANDARDS.md §15."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from goat_ai.config import Settings
from goat_ai.feature_gate_reasons import (
    GateKind,
    RUNTIME_DISABLED_BY_OPERATOR,
    RUNTIME_DOCKER_UNAVAILABLE,
)


@dataclass(frozen=True)
class CodeSandboxFeatureSnapshot:
    """Runtime / dependency readiness for the code-execution sandbox (not AuthZ)."""

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
    return "This feature is not available on this deployment."


def _docker_paths_to_probe(settings: Settings) -> list[Path]:
    raw = settings.docker_socket_path.strip()
    if raw:
        return [Path(raw)]
    if os.name == "nt":
        return [Path(r"\\.\pipe\docker_engine")]
    return [Path("/var/run/docker.sock")]


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
    for candidate in _docker_paths_to_probe(settings):
        if _path_usable_for_docker(candidate):
            return True
    return False


def compute_code_sandbox_snapshot(settings: Settings) -> CodeSandboxFeatureSnapshot:
    """Combine operator intent (config) with host probe for effective enablement."""
    allowed = settings.feature_code_sandbox_enabled
    if not allowed:
        return CodeSandboxFeatureSnapshot(
            allowed_by_config=False,
            available_on_host=False,
            effective_enabled=False,
            deny_reason=RUNTIME_DISABLED_BY_OPERATOR,
        )
    on_host = probe_docker_available(settings)
    if not on_host:
        return CodeSandboxFeatureSnapshot(
            allowed_by_config=True,
            available_on_host=False,
            effective_enabled=False,
            deny_reason=RUNTIME_DOCKER_UNAVAILABLE,
        )
    return CodeSandboxFeatureSnapshot(
        allowed_by_config=True,
        available_on_host=True,
        effective_enabled=True,
        deny_reason=None,
    )
