"""Controlled, documentable deny_reason values for feature gates (API-safe).

Do not expose raw exception text or internal diagnostics as ``deny_reason``.
See docs/ENGINEERING_STANDARDS.md §15.
"""

from __future__ import annotations

from typing import Final, Literal

# Runtime / deployment / dependency readiness (maps to HTTP 503 + FEATURE_UNAVAILABLE when enforced at route)
RUNTIME_DISABLED_BY_OPERATOR: Final = "disabled_by_operator"
RUNTIME_DOCKER_UNAVAILABLE: Final = "docker_unavailable"

# Authorization / policy (maps to HTTP 403 + FEATURE_DISABLED when enforced at route)
POLICY_PERMISSION_DENIED: Final = "permission_denied"

GateKind = Literal["policy", "runtime"]

PUBLIC_RUNTIME_REASONS: frozenset[str] = frozenset(
    {
        RUNTIME_DISABLED_BY_OPERATOR,
        RUNTIME_DOCKER_UNAVAILABLE,
    }
)
