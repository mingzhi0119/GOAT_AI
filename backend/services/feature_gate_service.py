"""Service boundary for capability-based feature gates (§15)."""

from __future__ import annotations

from backend.domain.authz_types import AuthorizationContext
from backend.services.exceptions import FeatureNotAvailable
from goat_ai.config import Settings
from goat_ai.feature_gates import (
    CodeSandboxFeatureSnapshot,
    compute_code_sandbox_snapshot,
)
from goat_ai.telemetry_counters import inc_feature_gate_denial


def get_code_sandbox_snapshot(settings: Settings) -> CodeSandboxFeatureSnapshot:
    """Return the current code-sandbox capability snapshot (no side effects)."""
    return compute_code_sandbox_snapshot(settings)


def code_sandbox_policy_allowed(auth_context: AuthorizationContext) -> bool:
    """Return whether the caller's credential scopes allow sandbox execution."""
    return "sandbox:execute" in auth_context.scopes


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
