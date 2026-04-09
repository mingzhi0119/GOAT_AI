"""Service boundary for capability-based feature gates (§15)."""

from __future__ import annotations

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


def require_code_sandbox_enabled(settings: Settings) -> None:
    """Enforce route/service layer: raise FeatureNotAvailable when not effectively enabled."""
    snap = compute_code_sandbox_snapshot(settings)
    if snap.effective_enabled:
        return
    reason = snap.deny_reason
    if reason is None:
        raise RuntimeError("code_sandbox snapshot missing deny_reason when disabled")
    inc_feature_gate_denial(feature="code_sandbox", reason=reason)
    raise FeatureNotAvailable(
        feature_id="code_sandbox",
        deny_reason=reason,
        gate_kind="runtime",
    )
