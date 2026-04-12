"""Service boundary for capability-based feature gates (§15)."""

from __future__ import annotations

from backend.domain.authz_types import AuthorizationContext
from backend.services.exceptions import FeatureNotAvailable
from goat_ai.config.settings import Settings
from goat_ai.config.feature_gates import (
    CodeSandboxFeatureSnapshot,
    RuntimeFeatureSnapshot,
    compute_agent_workbench_snapshot,
    compute_code_sandbox_snapshot,
)
from goat_ai.telemetry.telemetry_counters import inc_feature_gate_denial


def get_code_sandbox_snapshot(settings: Settings) -> CodeSandboxFeatureSnapshot:
    """Return the current code-sandbox capability snapshot (no side effects)."""
    return compute_code_sandbox_snapshot(settings)


def code_sandbox_policy_allowed(auth_context: AuthorizationContext) -> bool:
    """Return whether the caller's credential scopes allow sandbox execution."""
    return "sandbox:execute" in auth_context.scopes


def get_agent_workbench_snapshot(settings: Settings) -> RuntimeFeatureSnapshot:
    """Return the current shared workbench capability snapshot (no side effects)."""
    return compute_agent_workbench_snapshot(settings)


def require_code_sandbox_enabled(
    settings: Settings,
    auth_context: AuthorizationContext,
) -> None:
    """Enforce code-sandbox policy and runtime gates with stable semantics."""
    snap = compute_code_sandbox_snapshot(settings)
    if snap.effective_enabled:
        if code_sandbox_policy_allowed(auth_context):
            return
        inc_feature_gate_denial(
            feature="code_sandbox",
            gate_kind="policy",
            reason="permission_denied",
        )
        raise FeatureNotAvailable(
            feature_id="code_sandbox",
            deny_reason="permission_denied",
            gate_kind="policy",
        )
    reason = snap.deny_reason
    if reason is None:
        raise RuntimeError("code_sandbox snapshot missing deny_reason when disabled")
    inc_feature_gate_denial(
        feature="code_sandbox",
        gate_kind="runtime",
        reason=reason,
    )
    raise FeatureNotAvailable(
        feature_id="code_sandbox",
        deny_reason=reason,
        gate_kind="runtime",
    )


def require_agent_workbench_enabled(settings: Settings) -> None:
    """Enforce the shared workbench runtime gate with stable semantics."""
    snap = compute_agent_workbench_snapshot(settings)
    if snap.effective_enabled:
        return
    reason = snap.deny_reason
    if reason is None:
        raise RuntimeError("agent_workbench snapshot missing deny_reason when disabled")
    inc_feature_gate_denial(
        feature="agent_workbench",
        gate_kind="runtime",
        reason=reason,
    )
    raise FeatureNotAvailable(
        feature_id="agent_workbench",
        deny_reason=reason,
        gate_kind="runtime",
    )
